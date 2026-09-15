from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.universe_leaderboard import sync_score as sync_universe_score
from bot.config.game import (
    CELESTIAL_CARD_STARS,
    RELIC_BATTLE_GAME_DEADLINE_HOURS,
    RELIC_BATTLE_GAME_POOL,
    RELIC_BATTLE_GAMES_PER_MATCH,
    RELIC_BATTLE_THROWS_PER_GAME,
    RELIC_CHALLENGE_DECISION_HOURS,
)
from bot.constant.celestial import (
    TRANSACTION_REASON_DIVINE_GLOBAL,
    TRANSACTION_REASON_DIVINE_PSEUDO,
    TRANSACTION_REASON_DIVINE_UNIVERSE,
)
from bot.db.models.card import Card
from bot.db.models.celestial_battle import CelestialBattle
from bot.db.repositories import celestial as celestial_repo
from bot.db.repositories.inventory import add_card
from bot.services import battle_pass as pass_service
from bot.services.ubp import UbpAward, award_ubp

_BEST_OF = RELIC_BATTLE_GAMES_PER_MATCH
_WINS_NEEDED = _BEST_OF // 2 + 1  # 2 из 3


class NotChallengedError(Exception):
    """Нет ожидающего решения претендента (уже принято/отклонено/снято таймаутом)."""


class NoBattleError(Exception):
    pass


class NotParticipantError(Exception):
    pass


class AlreadyThrewError(Exception):
    """Игрок уже сделал все RELIC_BATTLE_THROWS_PER_GAME бросков этой игры."""


class GameExpiredError(Exception):
    """Дедлайн текущей игры истёк — сначала должен отработать sweep (см. main.py)."""


@dataclass
class DropOutcome:
    became_owner: bool  # False значит "стал претендентом"
    current_owner_id: int | None  # для претендента — кому слать пуш accept/decline


@dataclass
class DivineGrant:
    """Одна выданная божественная карта + всё, что нужно хендлеру, чтобы уведомить игрока и
    синхронизировать Redis-лидерборд вселенной ПОСЛЕ commit (см. `sync_after_award`)."""

    card: Card
    award: UbpAward
    user_id: int


@dataclass
class DivineAwards:
    """Побочные награды, которые могла вызвать смена владения одной небесной картой —
    хендлер использует это, чтобы показать игроку(ам) отдельное уведомление и досинхать
    лидерборды, если заодно досталась божественная карта. Список, а не одно поле — в
    редчайшем случае можно одновременно закрыть и global, и pseudo условие разным людям
    одним переходом (старый владелец получает pseudo, новый — global)."""

    grants: list[DivineGrant]


async def list_eligible_drop_cards(session: AsyncSession, *, universe_code: str, roller_id: int) -> list[Card]:
    return await celestial_repo.list_eligible_for_drop(session, universe_code=universe_code, roller_id=roller_id)


async def resolve_drop(session: AsyncSession, *, card: Card, user_id: int) -> DropOutcome | None:
    """Мутирует владение по факту дропа — карта уже выбрана `list_eligible_drop_cards` +
    random.choice в вызывающем коде (services/gacha). Возвращает None в крайне редкой
    гонке (два игрока выбили один и тот же дроп в одно мгновение) — тогда вызывающий код
    тихо откатывается на обычную карту (см. CLAUDE.md, "Небесные карты")."""
    ownership = await celestial_repo.get_ownership(session, card.id)
    if ownership is None:
        await celestial_repo.create_ownership(session, card_id=card.id, owner_id=user_id)
        return DropOutcome(became_owner=True, current_owner_id=None)

    deadline = datetime.now(timezone.utc) + timedelta(hours=RELIC_CHALLENGE_DECISION_HOURS)
    ok = await celestial_repo.try_set_challenger(session, card_id=card.id, challenger_id=user_id, deadline_at=deadline)
    if not ok:
        return None
    return DropOutcome(became_owner=False, current_owner_id=ownership.owner_id)


async def check_universe_completion(session: AsyncSession, *, user_id: int, universe_code: str, season_id: int) -> tuple[Card, UbpAward] | None:
    """"000"-божественная — полный сбор обычного (не небесного/божественного) ростера
    вселенной, порог считается динамически от реально засеянных карт (см. CLAUDE.md)."""
    divine_card = await celestial_repo.get_universe_divine_card(session, universe_code)
    if divine_card is None:
        return None
    if await celestial_repo.owns_card(session, user_id=user_id, card_id=divine_card.id):
        return None

    total = await celestial_repo.count_regular_cards(session, universe_code)
    if total == 0:
        return None
    owned = await celestial_repo.count_owned_regular_cards(session, user_id=user_id, universe_code=universe_code)
    if owned < total:
        return None

    await add_card(session, user_id=user_id, card_id=divine_card.id, stars=CELESTIAL_CARD_STARS, qty=1)
    award = await award_ubp(
        session,
        user_id=user_id,
        amount=divine_card.base_ubp,
        reason=TRANSACTION_REASON_DIVINE_UNIVERSE,
        universe_code=universe_code,
    )
    await pass_service.add_progress(session, user_id=user_id, season_id=season_id, real_ubp=divine_card.base_ubp)
    return divine_card, award


async def check_global_divine(session: AsyncSession, *, user_id: int, season_id: int) -> tuple[Card, UbpAward] | None:
    """"1000"-божественная — ОДНОВРЕМЕННОЕ владение всеми небесными картами разом. Должна
    вызываться КАЖДЫЙ раз, когда у `user_id` появляется небесная карта (дроп или победа в
    бою), ДО check_pseudo_divine (см. её докстринг — порядок важен)."""
    global_card = await celestial_repo.get_global_divine_card(session)
    if global_card is None:
        return None
    if await celestial_repo.owns_card(session, user_id=user_id, card_id=global_card.id):
        return None

    celestial_ids = [c.id for c in await celestial_repo.list_celestial_cards(session)]
    if not celestial_ids:
        return None
    owned_now = await celestial_repo.count_current_owner(session, user_id=user_id, card_ids=celestial_ids)
    if owned_now < len(celestial_ids):
        return None

    await add_card(session, user_id=user_id, card_id=global_card.id, stars=CELESTIAL_CARD_STARS, qty=1)
    award = await award_ubp(
        session,
        user_id=user_id,
        amount=global_card.base_ubp,
        reason=TRANSACTION_REASON_DIVINE_GLOBAL,
        universe_code=global_card.universe_code,
    )
    await pass_service.add_progress(session, user_id=user_id, season_id=season_id, real_ubp=global_card.base_ubp)
    return global_card, award


async def check_pseudo_divine(session: AsyncSession, *, user_id: int, season_id: int) -> tuple[Card, UbpAward] | None:
    """Псевдо-божественная (external_id "999", подтверждено пользователем 2026-09-15) —
    ТРЕТЬЯ отдельная карта, слабее "1000": игрок КОГДА-ЛИБО владел всеми небесными, но не
    одновременно. Должна вызываться ТОЛЬКО когда игрок ТЕРЯЕТ небесную карту (это
    единственное событие, которое может пополнить его "историю" настолько, чтобы покрыть
    все CELESTIAL_CARD_COUNT) — вызывающий код (`_transfer_after_loss`) сначала пишет
    CelestialHistory, потом вызывает эту функцию. Если игрок уже получил "1000" — не
    выдаётся вообще (та строго сильнее и покрывает то же условие полнее)."""
    pseudo_card = await celestial_repo.get_pseudo_divine_card(session)
    if pseudo_card is None:
        return None
    if await celestial_repo.owns_card(session, user_id=user_id, card_id=pseudo_card.id):
        return None
    global_card = await celestial_repo.get_global_divine_card(session)
    if global_card is not None and await celestial_repo.owns_card(session, user_id=user_id, card_id=global_card.id):
        return None

    celestial_ids = [c.id for c in await celestial_repo.list_celestial_cards(session)]
    if not celestial_ids:
        return None
    touched = await celestial_repo.count_ever_touched(session, user_id=user_id, card_ids=celestial_ids)
    if touched < len(celestial_ids):
        return None

    await add_card(session, user_id=user_id, card_id=pseudo_card.id, stars=CELESTIAL_CARD_STARS, qty=1)
    award = await award_ubp(
        session,
        user_id=user_id,
        amount=pseudo_card.base_ubp,
        reason=TRANSACTION_REASON_DIVINE_PSEUDO,
        universe_code=pseudo_card.universe_code,
    )
    await pass_service.add_progress(session, user_id=user_id, season_id=season_id, real_ubp=pseudo_card.base_ubp)
    return pseudo_card, award


async def _apply_divine_checks_after_transfer(
    session: AsyncSession, *, old_owner_id: int, new_owner_id: int, season_id: int
) -> DivineAwards:
    grants: list[DivineGrant] = []
    global_res = await check_global_divine(session, user_id=new_owner_id, season_id=season_id)
    if global_res is not None:
        grants.append(DivineGrant(card=global_res[0], award=global_res[1], user_id=new_owner_id))
    # Псевдо — только для того, кто ТЕРЯЕТ (см. её докстринг).
    pseudo_res = await check_pseudo_divine(session, user_id=old_owner_id, season_id=season_id)
    if pseudo_res is not None:
        grants.append(DivineGrant(card=pseudo_res[0], award=pseudo_res[1], user_id=old_owner_id))
    return DivineAwards(grants=grants)


async def _transfer_after_loss(
    session: AsyncSession, *, card_id: int, old_owner_id: int, new_owner_id: int, season_id: int
) -> DivineAwards:
    """Общий переход владения при ЛЮБОЙ потере (отказ/таймаут решения/проигрыш боя) — см.
    CLAUDE.md, "Небесные карты": все три случая эквивалентны. Не коммитит."""
    await celestial_repo.add_history(session, user_id=old_owner_id, card_id=card_id)
    await celestial_repo.transfer_ownership(session, card_id=card_id)
    return await _apply_divine_checks_after_transfer(
        session, old_owner_id=old_owner_id, new_owner_id=new_owner_id, season_id=season_id
    )


async def decline_challenge(
    session: AsyncSession, *, card_id: int, owner_id: int, season_id: int
) -> tuple[int, DivineAwards]:
    """Явный отказ владельца — тот же переход, что и таймаут решения (см. CLAUDE.md).
    Возвращает (challenger_id, побочные божественные награды) для уведомлений в хендлере.
    Одна логическая операция — коммитит сама (лист операции, см. правило 10)."""
    ownership = await celestial_repo.get_ownership(session, card_id)
    if ownership is None or ownership.owner_id != owner_id or ownership.challenger_id is None:
        raise NotChallengedError

    challenger_id = ownership.challenger_id
    awards = await _transfer_after_loss(
        session, card_id=card_id, old_owner_id=owner_id, new_owner_id=challenger_id, season_id=season_id
    )
    await session.commit()
    return challenger_id, awards


async def sweep_expired_decisions(session: AsyncSession, *, season_id: int) -> list[tuple[int, int, int, DivineAwards]]:
    """Претенденты, чей 6-часовой дедлайн решения истёк без ответа владельца — карта тихо
    уходит претенденту (см. CLAUDE.md). Возвращает список (card_id, old_owner_id,
    new_owner_id, побочные награды) для рассылки уведомлений вызывающим кодом. Коммитит
    ПОСЛЕ КАЖДОЙ карты отдельно (не одним commit на весь пакет в конце) — это N независимых
    переходов владения между разными парами игроков, а не один составной шаг правила 10;
    если данные одной карты по какой-то причине упадут с исключением, уже обработанные до
    неё карты не должны откатываться и обрабатываться повторно на следующем тике."""
    now = datetime.now(timezone.utc)
    expired = await celestial_repo.list_expired_decisions(session, now=now)
    results: list[tuple[int, int, int, DivineAwards]] = []
    for ownership in expired:
        old_owner_id, new_owner_id = ownership.owner_id, ownership.challenger_id
        awards = await _transfer_after_loss(
            session, card_id=ownership.card_id, old_owner_id=old_owner_id, new_owner_id=new_owner_id, season_id=season_id
        )
        await session.commit()
        results.append((ownership.card_id, old_owner_id, new_owner_id, awards))
    return results


async def accept_challenge(session: AsyncSession, *, card_id: int, owner_id: int) -> CelestialBattle:
    """Владелец принимает вызов — фиксирует 3 случайные игры и запускает первую (см.
    CLAUDE.md). Коммитит сама."""
    ownership = await celestial_repo.get_ownership(session, card_id)
    if ownership is None or ownership.owner_id != owner_id or ownership.challenger_id is None:
        raise NotChallengedError

    games = tuple(random.sample(RELIC_BATTLE_GAME_POOL, RELIC_BATTLE_GAMES_PER_MATCH))
    deadline = datetime.now(timezone.utc) + timedelta(hours=RELIC_BATTLE_GAME_DEADLINE_HOURS)
    battle = await celestial_repo.create_battle(
        session, card_id=card_id, owner_id=owner_id, challenger_id=ownership.challenger_id, games=games, deadline_at=deadline
    )
    # Дедлайн РЕШЕНИЯ больше не актуален — таймингом теперь управляет
    # CelestialBattle.game_deadline_at (см. её докстринг).
    ownership.challenge_deadline_at = None
    await session.commit()
    return battle


def _current_game(battle: CelestialBattle) -> str:
    return (battle.game_1, battle.game_2, battle.game_3)[battle.game_index]


@dataclass
class ThrowResult:
    card_id: int
    owner_id: int
    challenger_id: int
    battle: CelestialBattle | None  # None, если матч только что завершился (удалена сама строка)
    value: int
    game: str
    game_finished: bool
    match_finished: bool
    new_owner_id: int | None  # заполнено, только если матч только что завершился
    divine_awards: DivineAwards | None = None


async def throw_dice(
    session: AsyncSession, *, card_id: int, user_id: int, roll_value: int, season_id: int
) -> ThrowResult:
    """Записывает один бросок (значение уже получено в хендлере через
    `message.answer_dice()` — см. CLAUDE.md, правило 10: I/O с Telegram не место в сервисном
    слое) и, если это завершило текущую игру для ОБЕИХ сторон, сразу разрешает игру/матч.
    Одна логическая операция — коммитит сама."""
    battle = await celestial_repo.get_battle(session, card_id)
    if battle is None:
        raise NoBattleError
    if user_id not in (battle.owner_id, battle.challenger_id):
        raise NotParticipantError
    if datetime.now(timezone.utc) >= battle.game_deadline_at:
        raise GameExpiredError

    is_owner = user_id == battle.owner_id
    game = _current_game(battle)
    updated = await celestial_repo.record_throw(
        session, card_id=card_id, is_owner=is_owner, value=roll_value, max_throws=RELIC_BATTLE_THROWS_PER_GAME
    )
    if updated is None:
        raise AlreadyThrewError
    battle = updated

    both_done = (
        battle.owner_throw_count >= RELIC_BATTLE_THROWS_PER_GAME
        and battle.challenger_throw_count >= RELIC_BATTLE_THROWS_PER_GAME
    )
    if not both_done:
        await session.commit()
        return ThrowResult(
            card_id=battle.card_id,
            owner_id=battle.owner_id,
            challenger_id=battle.challenger_id,
            battle=battle,
            value=roll_value,
            game=game,
            game_finished=False,
            match_finished=False,
            new_owner_id=None,
        )

    return await _resolve_game(session, battle, roll_value=roll_value, game=game, season_id=season_id)


async def _resolve_game(
    session: AsyncSession, battle: CelestialBattle, *, roll_value: int, game: str, season_id: int
) -> ThrowResult:
    owner_won_game = battle.owner_throw_sum >= battle.challenger_throw_sum  # ничья -> владелец (см. CLAUDE.md/докстринг)
    match_decided = (battle.owner_wins + (1 if owner_won_game else 0) >= _WINS_NEEDED) or (
        battle.challenger_wins + (0 if owner_won_game else 1) >= _WINS_NEEDED
    )
    is_last_game = battle.game_index + 1 >= RELIC_BATTLE_GAMES_PER_MATCH
    match_finished = match_decided or is_last_game

    new_deadline = None if match_finished else datetime.now(timezone.utc) + timedelta(hours=RELIC_BATTLE_GAME_DEADLINE_HOURS)
    battle = await celestial_repo.advance_game(session, card_id=battle.card_id, owner_won_game=owner_won_game, new_deadline_at=new_deadline)

    if not match_finished:
        await session.commit()
        return ThrowResult(
            card_id=battle.card_id,
            owner_id=battle.owner_id,
            challenger_id=battle.challenger_id,
            battle=battle,
            value=roll_value,
            game=game,
            game_finished=True,
            match_finished=False,
            new_owner_id=None,
        )

    return await _finish_battle(session, battle, roll_value=roll_value, game=game, season_id=season_id)


async def _finish_battle(
    session: AsyncSession, battle: CelestialBattle, *, roll_value: int, game: str, season_id: int
) -> ThrowResult:
    owner_wins_match = battle.owner_wins > battle.challenger_wins
    card_id, owner_id, challenger_id = battle.card_id, battle.owner_id, battle.challenger_id
    await celestial_repo.delete_battle(session, card_id=card_id)

    divine_awards: DivineAwards | None = None
    new_owner_id: int
    if owner_wins_match:
        await celestial_repo.clear_challenge(session, card_id=card_id)
        new_owner_id = owner_id
    else:
        divine_awards = await _transfer_after_loss(
            session, card_id=card_id, old_owner_id=owner_id, new_owner_id=challenger_id, season_id=season_id
        )
        new_owner_id = challenger_id

    await session.commit()
    return ThrowResult(
        card_id=card_id,
        owner_id=owner_id,
        challenger_id=challenger_id,
        battle=None,
        value=roll_value,
        game=game,
        game_finished=True,
        match_finished=True,
        new_owner_id=new_owner_id,
        divine_awards=divine_awards,
    )


async def sweep_expired_games(session: AsyncSession, *, season_id: int) -> list[ThrowResult]:
    """Игры, чей часовой дедлайн истёк, а кто-то (или оба) не успел бросить все 3 раза —
    засчитывается техническое поражение той стороне, у которой МЕНЬШЕ бросков (при равном
    числе — по сумме, при полном совпадении — владельцу, тот же принцип, что обычная ничья
    внутри игры, см. _resolve_game). Коммитит сама — самостоятельная операция фонового
    шедулера."""
    now = datetime.now(timezone.utc)
    results: list[ThrowResult] = []
    for battle in await celestial_repo.list_expired_games(session, now=now):
        game = _current_game(battle)
        if battle.owner_throw_count != battle.challenger_throw_count:
            owner_won_game = battle.owner_throw_count > battle.challenger_throw_count
        else:
            owner_won_game = battle.owner_throw_sum >= battle.challenger_throw_sum
        results.append(await _finalize_expired_game(session, battle, owner_won_game=owner_won_game, game=game, season_id=season_id))
    return results


async def _finalize_expired_game(
    session: AsyncSession, battle: CelestialBattle, *, owner_won_game: bool, game: str, season_id: int
) -> ThrowResult:
    match_decided = (battle.owner_wins + (1 if owner_won_game else 0) >= _WINS_NEEDED) or (
        battle.challenger_wins + (0 if owner_won_game else 1) >= _WINS_NEEDED
    )
    is_last_game = battle.game_index + 1 >= RELIC_BATTLE_GAMES_PER_MATCH
    match_finished = match_decided or is_last_game

    new_deadline = None if match_finished else datetime.now(timezone.utc) + timedelta(hours=RELIC_BATTLE_GAME_DEADLINE_HOURS)
    battle = await celestial_repo.advance_game(session, card_id=battle.card_id, owner_won_game=owner_won_game, new_deadline_at=new_deadline)

    if not match_finished:
        await session.commit()
        return ThrowResult(
            card_id=battle.card_id,
            owner_id=battle.owner_id,
            challenger_id=battle.challenger_id,
            battle=battle,
            value=-1,
            game=game,
            game_finished=True,
            match_finished=False,
            new_owner_id=None,
        )
    return await _finish_battle(session, battle, roll_value=-1, game=game, season_id=season_id)


async def sync_grant(redis: Redis, season_id: int, grant: DivineGrant) -> None:
    """Общий хвост после ЛЮБОЙ выданной божественной карты — синхронизирует Redis-лидерборд
    вселенной ПОСЛЕ commit (см. CLAUDE.md, правило 10). Общий глобальный лидерборд
    синхронизирует вызывающий код (services/gacha уже это делает для самой крутки) — здесь
    только вселенческий, специфичный для этого домена."""
    await sync_universe_score(redis, season_id, grant.card.universe_code, grant.user_id, grant.award.universe_ubp_season)
