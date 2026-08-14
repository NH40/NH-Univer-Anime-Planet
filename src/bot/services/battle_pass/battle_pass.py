from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.game import (
    BATTLE_PASS_BOOST_TIER_LEVELS,
    BATTLE_PASS_CYCLE_LEVELS,
    battle_pass_boost_multiplier,
    battle_pass_cumulative,
    battle_pass_free_reward,
    battle_pass_level_from_progress,
    battle_pass_premium_reward,
)
from bot.constant.battle_pass import TRACK_FREE, TRACK_PREMIUM, TRANSACTION_REASON_PASS_FREE, TRANSACTION_REASON_PASS_PREMIUM
from bot.db.models.battle_pass import BattlePass
from bot.db.models.enums import TransactionCurrency
from bot.db.models.transaction import Transaction
from bot.db.repositories import battle_pass as pass_repo
from bot.db.repositories import season as season_repo
from bot.db.repositories.user import add_coins, add_dust
from bot.services import ticket

Track = Literal["free", "premium"]

LEVELS_PER_PAGE = 10
_DAILY_BOOST_CAP = BATTLE_PASS_BOOST_TIER_LEVELS[-1]


class NoSeasonActiveError(Exception):
    pass


class NotPremiumError(Exception):
    pass


class NothingToClaimError(Exception):
    """Для claim_all — во всём диапазоне claimed+1..текущий нечего забирать."""


class LevelLockedError(Exception):
    """Уровень ещё не разблокирован прогрессом (level > текущий уровень)."""


class LevelAlreadyClaimedError(Exception):
    """Уровень уже забран — либо входит в сплошной high-water mark, либо был забран вне
    очереди раньше (см. BattlePassClaim)."""


def _reward(track: Track, level: int) -> tuple[int, int, int]:
    """(пыль, тикеты, коины) за ОДИН конкретный уровень этой ветки — коины всегда 0 для
    бесплатной. Награда циклится по позиции внутри круга и не растёт с уровнем (см.
    CLAUDE.md, "Сезонный пасс") — обе формулы уже это учитывают."""
    if track == TRACK_FREE:
        dust, tickets = battle_pass_free_reward(level)
        return dust, tickets, 0
    return battle_pass_premium_reward(level)


def _reason(track: Track) -> str:
    return TRANSACTION_REASON_PASS_FREE if track == TRACK_FREE else TRANSACTION_REASON_PASS_PREMIUM


def _claimed_level(row, track: Track) -> int:
    return row.claimed_free_level if track == TRACK_FREE else row.claimed_premium_level


async def _grant(session: AsyncSession, *, user_id: int, track: Track, dust: int, tickets: int, coins: int) -> None:
    reason = _reason(track)
    if dust:
        await add_dust(session, user_id=user_id, amount=dust)
        session.add(Transaction(user_id=user_id, currency=TransactionCurrency.dust, amount=dust, reason=reason))
    if tickets:
        await ticket.grant(session, user_id, tickets)
        session.add(Transaction(user_id=user_id, currency=TransactionCurrency.tickets, amount=tickets, reason=reason))
    if coins:
        await add_coins(session, user_id=user_id, amount=coins)
        session.add(Transaction(user_id=user_id, currency=TransactionCurrency.coins, amount=coins, reason=reason))


async def claim_level(session: AsyncSession, *, user_id: int, track: Track, level: int) -> tuple[int, int, int]:
    """Забирает награду ОДНОГО конкретного уровня одной ветки — тап по любой доступной
    ячейке в любом порядке (подтверждено пользователем 2026-08-11, см. CLAUDE.md, "Сезонный
    пасс: клейм произвольной ячейки"). Одна логическая операция — один commit. Возвращает
    (пыль, тикеты, коины)."""
    season = await season_repo.get_active(session)
    if season is None:
        raise NoSeasonActiveError

    row = await pass_repo.get_or_create(session, user_id=user_id, season_id=season.id)
    if track == TRACK_PREMIUM and not row.is_premium:
        raise NotPremiumError

    current_level = battle_pass_level_from_progress(row.progress)
    if level < 1 or level > current_level:
        raise LevelLockedError

    claimed_level = _claimed_level(row, track)
    if level <= claimed_level:
        raise LevelAlreadyClaimedError
    if await pass_repo.claim_exists(session, user_id=user_id, season_id=season.id, track=track, level=level):
        raise LevelAlreadyClaimedError

    dust, tickets, coins = _reward(track, level)
    await _grant(session, user_id=user_id, track=track, dust=dust, tickets=tickets, coins=coins)

    if level == claimed_level + 1:
        # Продвигаем high-water mark и поглощаем подряд идущие внеочередные клеймы, уже
        # лежащие в battle_pass_claims следом (иначе они остались бы там мёртвым весом).
        pending = await pass_repo.list_claims(session, user_id=user_id, season_id=season.id, track=track)
        new_level = level
        absorbed: list[int] = []
        while (new_level + 1) in pending:
            new_level += 1
            absorbed.append(new_level)
        if absorbed:
            await pass_repo.delete_claims(session, user_id=user_id, season_id=season.id, track=track, levels=absorbed)
        await pass_repo.set_claimed_level(session, user_id=user_id, season_id=season.id, track=track, level=new_level)
    else:
        await pass_repo.add_claim(session, user_id=user_id, season_id=season.id, track=track, level=level)

    await session.commit()
    return dust, tickets, coins


@dataclass
class ClaimAllResult:
    dust: int
    tickets: int
    coins: int
    count: int
    current_level: int


async def claim_all(session: AsyncSession, *, user_id: int, track: Track) -> ClaimAllResult:
    """Забирает разом ВСЕ незабранные уровни ветки от claimed+1 до текущего (старое
    поведение клейма, сохранено как отдельная кнопка "Забрать всё" — см. CLAUDE.md). Одна
    логическая операция — один commit."""
    season = await season_repo.get_active(session)
    if season is None:
        raise NoSeasonActiveError

    row = await pass_repo.get_or_create(session, user_id=user_id, season_id=season.id)
    if track == TRACK_PREMIUM and not row.is_premium:
        raise NotPremiumError

    current_level = battle_pass_level_from_progress(row.progress)
    claimed_level = _claimed_level(row, track)
    if current_level <= claimed_level:
        raise NothingToClaimError

    already_claimed = await pass_repo.list_claims(session, user_id=user_id, season_id=season.id, track=track)

    total_dust = total_tickets = total_coins = count = 0
    for lvl in range(claimed_level + 1, current_level + 1):
        if lvl in already_claimed:
            continue  # уже забран вне очереди раньше — не начислять повторно
        dust, tickets, coins = _reward(track, lvl)
        total_dust += dust
        total_tickets += tickets
        total_coins += coins
        count += 1

    if count == 0:
        raise NothingToClaimError

    await _grant(session, user_id=user_id, track=track, dust=total_dust, tickets=total_tickets, coins=total_coins)
    await pass_repo.set_claimed_level(session, user_id=user_id, season_id=season.id, track=track, level=current_level)
    await pass_repo.clear_claims(session, user_id=user_id, season_id=season.id, track=track)

    await session.commit()
    return ClaimAllResult(dust=total_dust, tickets=total_tickets, coins=total_coins, count=count, current_level=current_level)


async def add_progress(session: AsyncSession, *, user_id: int, season_id: int, real_ubp: int) -> None:
    """Начисляет прогресс Battle Pass, ускоренный дневным бустом (см. CLAUDE.md, "Сезонный
    пасс: 500 циклических уровней") — вызывается ПАРАЛЛЕЛЬНО с `services.ubp.award_ubp` из
    тех же составных операций (крутка, слияние), той же транзакцией, без своего commit
    (правило 10) — коммитит вызывающий сервис верхнего уровня. НЕ трогает `User.ubp_season`:
    тот остаётся источником для лидерборда/войн кланов, буст касается только скорости
    заполнения Battle Pass.

    Осознанное упрощение: множитель берётся ОДИН раз на всё событие целиком (не
    пересчитывается по уровню внутри одного крупного начисления, теоретически пересекающего
    границу тира буста) — типичное начисление UBP за раз небольшое, риск заметного
    расхождения исчезающе мал, а honest per-level цикл сильно усложнил бы код без реальной
    пользы."""
    if real_ubp <= 0:
        return

    row = await pass_repo.get_or_create_locked(session, user_id=user_id, season_id=season_id)

    today = datetime.now(timezone.utc).date()
    used_today = row.boost_levels_used_today if row.boost_date == today else 0

    multiplier = battle_pass_boost_multiplier(used_today)
    boosted = real_ubp * multiplier

    old_level = battle_pass_level_from_progress(row.progress)
    new_progress = row.progress + boosted
    new_level = battle_pass_level_from_progress(new_progress)

    new_used_today = min(_DAILY_BOOST_CAP, used_today + (new_level - old_level))

    await pass_repo.update_progress(
        session,
        user_id=user_id,
        season_id=season_id,
        progress=new_progress,
        boost_levels_used_today=new_used_today,
        boost_date=today,
    )


@dataclass
class BoostStatus:
    """Только для отображения (см. CLAUDE.md, "Mini App: редизайн"/дневной буст) — сама
    логика расчёта и продвижения буста живёт в add_progress(), эта функция её не
    повторяет, только читает уже посчитанные boost_levels_used_today/boost_date той же
    лениво-сбрасываемой логикой (используется ЛЕНИВОЕ обнуление "used_today", если
    boost_date не сегодня — точная копия того, что уже делает add_progress)."""

    multiplier: int
    used_today: int
    cap: int
    seconds_until_reset: int


def _boost_status_from_row(row: BattlePass) -> BoostStatus:
    today = datetime.now(timezone.utc).date()
    used_today = row.boost_levels_used_today if row.boost_date == today else 0
    multiplier = battle_pass_boost_multiplier(used_today)
    tomorrow = datetime.combine(today + timedelta(days=1), time.min, tzinfo=timezone.utc)
    seconds_until_reset = int((tomorrow - datetime.now(timezone.utc)).total_seconds())
    return BoostStatus(
        multiplier=multiplier, used_today=used_today, cap=_DAILY_BOOST_CAP, seconds_until_reset=max(0, seconds_until_reset)
    )


async def get_boost_status(session: AsyncSession, *, user_id: int, season_id: int) -> BoostStatus:
    """Read-only статус дневного буста — для экранов, которым не нужна вся `list_levels()`
    целиком (сейчас используется только там же, но вынесено отдельно на случай других
    точек входа, см. CLAUDE.md)."""
    row = await pass_repo.get_or_create(session, user_id=user_id, season_id=season_id)
    return _boost_status_from_row(row)


@dataclass
class LevelEntry:
    level: int  # абсолютный номер уровня (растёт бесконечно, награда циклится по позиции)
    free_dust: int
    free_tickets: int
    premium_dust: int
    premium_tickets: int
    premium_coins: int
    unlocked: bool
    free_claimed: bool
    premium_claimed: bool


@dataclass
class LevelsPage:
    entries: list[LevelEntry]
    page: int
    total_pages: int
    current_level: int
    is_premium: bool
    progress: int  # BattlePass.progress — сколько накоплено сейчас
    level_floor: int  # сколько нужно было, чтобы достичь текущего уровня
    level_ceiling: int  # сколько нужно для следующего уровня
    # high-water mark каждой ветки (не привязаны к текущей странице) — чтобы UI мог решить,
    # показывать ли кнопку "Забрать всё", даже когда все незабранные уровни лежат на ДРУГОЙ
    # странице, а не на той, что сейчас отрисована.
    claimed_free_level: int
    claimed_premium_level: int
    boost: BoostStatus


def _circle_offset(current_level: int) -> int:
    if current_level <= 0:
        return 0
    return ((current_level - 1) // BATTLE_PASS_CYCLE_LEVELS) * BATTLE_PASS_CYCLE_LEVELS


def page_for_level(level: int, *, current_level: int, per_page: int = LEVELS_PER_PAGE) -> int:
    """Номер страницы (в текущем круге игрока), на которой лежит `level` — используется
    и для дефолтного открытия экрана (см. list_levels, page=None), и для редиректа после
    "Забрать всё" (см. CLAUDE.md, "Сезонный пасс: клейм произвольной ячейки"). `per_page`
    параметризован — бот и Mini App показывают разное число уровней на странице (см.
    list_levels), у каждого свой смысл у номера страницы."""
    offset = _circle_offset(current_level)
    pos = max(1, min(level - offset, BATTLE_PASS_CYCLE_LEVELS))
    return -(-pos // per_page)


async def list_levels(
    session: AsyncSession, *, user_id: int, page: int | None, per_page: int = LEVELS_PER_PAGE
) -> LevelsPage | None:
    """Пагинированная лента уровней текущего 500-уровневого круга (не всей бесконечной
    истории) — общая формула для бота и Mini App, ничего не дублируется на два стека.
    Уровни якорятся на ТЕКУЩИЙ круг игрока: если игрок уже прошёл цикл 500 уровней целиком,
    страница 1 показывает уровни (500×circle + 1).. , а не 1.. — иначе статус
    "забрано"/"доступно" не совпадал бы с реальным `claimed_free_level`.

    `per_page` — Mini App использует дефолт (горизонтальная лента, скроллится), бот просит
    меньше (см. `handlers/battle_pass/levels.py` — 2 горизонтальные строки кнопок вместо
    вертикального списка, подтверждено пользователем 2026-08-11).

    `page=None` — открыть на странице с ПЕРВЫМ незабранным уровнем (по любой из открытых
    веток), а не всегда с первой страницы круга (см. CLAUDE.md — раньше дефолтная страница
    не учитывала прогресс, и на дальних кругах приходилось пролистывать вручную)."""
    season = await season_repo.get_active(session)
    if season is None:
        return None

    row = await pass_repo.get_or_create(session, user_id=user_id, season_id=season.id)
    current_level = battle_pass_level_from_progress(row.progress)
    circle_offset = _circle_offset(current_level)

    free_claims = await pass_repo.list_claims(session, user_id=user_id, season_id=season.id, track=TRACK_FREE)
    premium_claims = (
        await pass_repo.list_claims(session, user_id=user_id, season_id=season.id, track=TRACK_PREMIUM)
        if row.is_premium
        else set()
    )

    total_pages = -(-BATTLE_PASS_CYCLE_LEVELS // per_page)
    if page is None:
        anchor_level = min(row.claimed_free_level, row.claimed_premium_level if row.is_premium else row.claimed_free_level) + 1
        page = page_for_level(anchor_level, current_level=current_level, per_page=per_page)
    page = max(1, min(page, total_pages))
    start_pos = (page - 1) * per_page + 1
    end_pos = min(start_pos + per_page - 1, BATTLE_PASS_CYCLE_LEVELS)

    entries = []
    for pos in range(start_pos, end_pos + 1):
        level = circle_offset + pos
        free_dust, free_tickets = battle_pass_free_reward(level)
        premium_dust, premium_tickets, premium_coins = battle_pass_premium_reward(level)
        entries.append(
            LevelEntry(
                level=level,
                free_dust=free_dust,
                free_tickets=free_tickets,
                premium_dust=premium_dust,
                premium_tickets=premium_tickets,
                premium_coins=premium_coins,
                unlocked=current_level >= level,
                free_claimed=(level <= row.claimed_free_level) or (level in free_claims),
                premium_claimed=(level <= row.claimed_premium_level) or (level in premium_claims),
            )
        )

    return LevelsPage(
        entries=entries,
        page=page,
        total_pages=total_pages,
        current_level=current_level,
        is_premium=row.is_premium,
        progress=row.progress,
        level_floor=battle_pass_cumulative(current_level),
        level_ceiling=battle_pass_cumulative(current_level + 1),
        claimed_free_level=row.claimed_free_level,
        claimed_premium_level=row.claimed_premium_level,
        boost=_boost_status_from_row(row),
    )


async def is_premium(session: AsyncSession, *, user_id: int) -> bool:
    """Только для экранов вне Battle Pass, которым нужен один булев статус (например,
    магазин — см. handlers/shop._battle_pass_text) — не тянуть весь list_levels ради этого."""
    season = await season_repo.get_active(session)
    if season is None:
        return False
    row = await pass_repo.get_or_create(session, user_id=user_id, season_id=season.id)
    return row.is_premium
