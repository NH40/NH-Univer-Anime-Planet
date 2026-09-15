from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.card import Card
from bot.db.models.celestial_battle import CelestialBattle
from bot.db.models.celestial_history import CelestialHistory
from bot.db.models.celestial_ownership import CelestialOwnership
from bot.db.models.inventory import UserCard

# --- Карты (небесные/божественные) ---


async def list_celestial_cards(session: AsyncSession) -> list[Card]:
    result = await session.execute(select(Card).where(Card.is_celestial.is_(True)))
    return list(result.scalars().all())


async def list_eligible_for_drop(session: AsyncSession, *, universe_code: str, roller_id: int) -> list[Card]:
    """Небесные карты ЭТОЙ вселенной, на которые роллер сейчас МОГ БЫ выпасть — слот либо
    вообще свободен (карта ни разу не выпадала), либо занят кем-то другим и претендент ещё
    не назначен (см. CLAUDE.md, "Небесные карты": второй претендент невозможен). Уже
    отфильтровывает случай "роллер уже сам владелец" — иначе он "выбивал" бы сам у себя."""
    result = await session.execute(
        select(Card)
        .outerjoin(CelestialOwnership, CelestialOwnership.card_id == Card.id)
        .where(
            Card.is_celestial.is_(True),
            Card.universe_code == universe_code,
            (CelestialOwnership.card_id.is_(None))
            | ((CelestialOwnership.challenger_id.is_(None)) & (CelestialOwnership.owner_id != roller_id)),
        )
    )
    return list(result.scalars().all())


async def get_universe_divine_card(session: AsyncSession, universe_code: str) -> Card | None:
    """"000"-вариант божественной карты ЭТОЙ вселенной (см. Card.is_divine_global) — None,
    если админ ещё не завёл её в assets/divine/divine.csv для этой вселенной (штатное
    состояние "ещё не настроено", не ошибка, см. scripts/seed_relics.py)."""
    result = await session.execute(
        select(Card).where(Card.universe_code == universe_code, Card.is_divine.is_(True), Card.is_divine_global.is_(False))
    )
    return result.scalars().first()


async def get_global_divine_card(session: AsyncSession) -> Card | None:
    """"1000"-вариант — не путать с get_pseudo_divine_card ниже (та слабее, третья
    отдельная карта, см. Card.is_divine_pseudo)."""
    result = await session.execute(
        select(Card).where(Card.is_divine.is_(True), Card.is_divine_global.is_(True), Card.is_divine_pseudo.is_(False))
    )
    return result.scalars().first()


async def get_pseudo_divine_card(session: AsyncSession) -> Card | None:
    result = await session.execute(
        select(Card).where(Card.is_divine.is_(True), Card.is_divine_global.is_(True), Card.is_divine_pseudo.is_(True))
    )
    return result.scalars().first()


async def owns_card(session: AsyncSession, *, user_id: int, card_id: int) -> bool:
    """Быстрая проверка "уже есть хоть одна копия" — дешёвый ранний выход перед тяжёлой
    проверкой полноты ростера (см. services/celestial.check_universe_completion): типичный
    игрок, который уже получил божественную карту, не должен на каждой крутке пересчитывать
    COUNT DISTINCT по всей своей коллекции вселенной."""
    result = await session.execute(
        select(func.count()).select_from(UserCard).where(
            UserCard.user_id == user_id, UserCard.card_id == card_id, UserCard.quantity > 0
        )
    )
    return result.scalar_one() > 0


async def count_regular_cards(session: AsyncSession, universe_code: str) -> int:
    """Сколько ОБЫЧНЫХ (не небесных, не божественных) карт существует в этой вселенной —
    растёт динамически при добавлении новых карт (см. CLAUDE.md — порог НЕ фиксирован
    числом 200, вычисляется от реально засеянных карт)."""
    result = await session.execute(
        select(func.count()).select_from(Card).where(
            Card.universe_code == universe_code, Card.is_celestial.is_(False), Card.is_divine.is_(False)
        )
    )
    return result.scalar_one()


async def count_owned_regular_cards(session: AsyncSession, *, user_id: int, universe_code: str) -> int:
    result = await session.execute(
        select(func.count(func.distinct(Card.id)))
        .select_from(Card)
        .join(UserCard, (UserCard.card_id == Card.id) & (UserCard.user_id == user_id) & (UserCard.quantity > 0))
        .where(Card.universe_code == universe_code, Card.is_celestial.is_(False), Card.is_divine.is_(False))
    )
    return result.scalar_one()


# --- Владение/претендент ---


async def get_ownership(session: AsyncSession, card_id: int) -> CelestialOwnership | None:
    return await session.get(CelestialOwnership, card_id)


async def create_ownership(session: AsyncSession, *, card_id: int, owner_id: int) -> CelestialOwnership:
    """Первый дроп этой небесной карты кому-либо — строки ещё не было (см.
    CelestialOwnership docstring). Не коммитит — часть составной операции крутки."""
    ownership = CelestialOwnership(card_id=card_id, owner_id=owner_id)
    session.add(ownership)
    await session.flush()
    return ownership


async def try_set_challenger(
    session: AsyncSession, *, card_id: int, challenger_id: int, deadline_at: datetime
) -> bool:
    """Атомарно ставит претендента — ТОЛЬКО если слот сейчас свободен (challenger_id IS
    NULL и это не сам владелец), иначе ничего не меняет (см. правило 1 — гонка второго
    претендента закрывается условием в WHERE, не отдельным Redis-локом: два игрока
    физически не могут одновременно выбить один и тот же дроп, но на всякий случай проверка
    здесь тоже атомарна). Возвращает True, если претендент реально поставлен."""
    result = await session.execute(
        update(CelestialOwnership)
        .where(
            CelestialOwnership.card_id == card_id,
            CelestialOwnership.challenger_id.is_(None),
            CelestialOwnership.owner_id != challenger_id,
        )
        .values(challenger_id=challenger_id, challenge_deadline_at=deadline_at)
    )
    return result.rowcount > 0


async def transfer_ownership(session: AsyncSession, *, card_id: int) -> CelestialOwnership:
    """Претендент становится владельцем (проигрыш/таймаут/отказ бывшего владельца — во всех
    трёх случаях один и тот же переход, см. CLAUDE.md, "Небесные карты"). Слот полностью
    освобождается — новый претендент сможет появиться со следующего дропа."""
    ownership = await session.get(CelestialOwnership, card_id)
    assert ownership is not None and ownership.challenger_id is not None
    ownership.owner_id = ownership.challenger_id
    ownership.challenger_id = None
    ownership.challenge_deadline_at = None
    await session.flush()
    return ownership


async def clear_challenge(session: AsyncSession, *, card_id: int) -> None:
    """Владелец отбился (выиграл бой) — претендент снимается, карта остаётся у владельца."""
    await session.execute(
        update(CelestialOwnership)
        .where(CelestialOwnership.card_id == card_id)
        .values(challenger_id=None, challenge_deadline_at=None)
    )


async def list_expired_decisions(session: AsyncSession, *, now: datetime) -> list[CelestialOwnership]:
    """Претенденты, чей дедлайн решения владельца (6ч) истёк, а владелец так и не принял
    вызов (иначе уже была бы строка в celestial_battles) — см.
    services/celestial.sweep_expired_decisions."""
    result = await session.execute(
        select(CelestialOwnership)
        .outerjoin(CelestialBattle, CelestialBattle.card_id == CelestialOwnership.card_id)
        .where(
            CelestialOwnership.challenger_id.is_not(None),
            CelestialOwnership.challenge_deadline_at <= now,
            CelestialBattle.card_id.is_(None),
        )
    )
    return list(result.scalars().all())


@dataclass
class CelestialCardStatus:
    card: Card
    ownership: CelestialOwnership | None
    battle: CelestialBattle | None


async def list_all_statuses(session: AsyncSession) -> list[CelestialCardStatus]:
    """Все небесные карты с их текущим статусом владения — для экрана "Небесные карты"
    (см. CLAUDE.md). Небольшой фиксированный список (CELESTIAL_CARD_COUNT), без пагинации
    на уровне SQL, три отдельных запроса читаемее одного огромного тройного LEFT JOIN."""
    cards = (
        (await session.execute(select(Card).where(Card.is_celestial.is_(True)).order_by(Card.universe_code, Card.external_id)))
        .scalars()
        .all()
    )
    if not cards:
        return []
    card_ids = [c.id for c in cards]
    ownerships = {
        o.card_id: o
        for o in (await session.execute(select(CelestialOwnership).where(CelestialOwnership.card_id.in_(card_ids)))).scalars()
    }
    battles = {
        b.card_id: b
        for b in (await session.execute(select(CelestialBattle).where(CelestialBattle.card_id.in_(card_ids)))).scalars()
    }
    return [
        CelestialCardStatus(card=card, ownership=ownerships.get(card.id), battle=battles.get(card.id)) for card in cards
    ]


# --- История владения (псевдо-божественная) ---


async def add_history(session: AsyncSession, *, user_id: int, card_id: int) -> None:
    stmt = (
        pg_insert(CelestialHistory)
        .values(user_id=user_id, card_id=card_id)
        .on_conflict_do_nothing(index_elements=[CelestialHistory.user_id, CelestialHistory.card_id])
    )
    await session.execute(stmt)


async def count_ever_touched(session: AsyncSession, *, user_id: int, card_ids: list[int]) -> int:
    """Сколько из перечисленных небесных карт игрок ЛИБО владеет прямо сейчас, ЛИБО когда-то
    владел и потерял (объединение CelestialOwnership.owner_id + CelestialHistory) — основа
    проверки псевдо-божественной карты (см. services/celestial.check_pseudo_divine)."""
    current = select(CelestialOwnership.card_id).where(
        CelestialOwnership.owner_id == user_id, CelestialOwnership.card_id.in_(card_ids)
    )
    past = select(CelestialHistory.card_id).where(
        CelestialHistory.user_id == user_id, CelestialHistory.card_id.in_(card_ids)
    )
    # UNION (не UNION ALL) уже дедуплицирует card_id, встречающийся в обеих выборках сразу
    # (текущий владелец, который до этого те же самые копии не терял, туда и не попадёт из
    # past — но на всякий случай, если когда-нибудь получится и там, и там).
    union_subq = current.union(past).subquery()
    result = await session.execute(select(func.count()).select_from(union_subq))
    return result.scalar_one()


async def count_current_owner(session: AsyncSession, *, user_id: int, card_ids: list[int]) -> int:
    """Сколько из перечисленных небесных карт игрок владеет ПРЯМО СЕЙЧАС — основа проверки
    полной божественной карты (см. services/celestial.check_global_divine): нужно
    ОДНОВРЕМЕННОЕ владение всеми, не когда-либо."""
    result = await session.execute(
        select(func.count())
        .select_from(CelestialOwnership)
        .where(CelestialOwnership.owner_id == user_id, CelestialOwnership.card_id.in_(card_ids))
    )
    return result.scalar_one()


# --- Бой ---


async def create_battle(
    session: AsyncSession,
    *,
    card_id: int,
    owner_id: int,
    challenger_id: int,
    games: tuple[str, str, str],
    deadline_at: datetime,
) -> CelestialBattle:
    battle = CelestialBattle(
        card_id=card_id,
        owner_id=owner_id,
        challenger_id=challenger_id,
        game_1=games[0],
        game_2=games[1],
        game_3=games[2],
        game_deadline_at=deadline_at,
    )
    session.add(battle)
    await session.flush()
    return battle


async def get_battle(session: AsyncSession, card_id: int) -> CelestialBattle | None:
    return await session.get(CelestialBattle, card_id)


async def record_throw(session: AsyncSession, *, card_id: int, is_owner: bool, value: int, max_throws: int) -> CelestialBattle | None:
    """Атомарно добавляет один бросок нужной стороне, ТОЛЬКО если у неё ещё не набрано
    max_throws бросков в текущей игре (правило 1 — условие прямо в WHERE, гонка второго
    клика по "Бросить" от того же игрока просто не пройдёт условие и вернёт None).
    Возвращает обновлённую строку боя или None, если бросков уже было max_throws."""
    if is_owner:
        stmt = (
            update(CelestialBattle)
            .where(CelestialBattle.card_id == card_id, CelestialBattle.owner_throw_count < max_throws)
            .values(owner_throw_count=CelestialBattle.owner_throw_count + 1, owner_throw_sum=CelestialBattle.owner_throw_sum + value)
        )
    else:
        stmt = (
            update(CelestialBattle)
            .where(CelestialBattle.card_id == card_id, CelestialBattle.challenger_throw_count < max_throws)
            .values(
                challenger_throw_count=CelestialBattle.challenger_throw_count + 1,
                challenger_throw_sum=CelestialBattle.challenger_throw_sum + value,
            )
        )
    result = await session.execute(stmt.returning(CelestialBattle))
    return result.scalar_one_or_none()


async def advance_game(
    session: AsyncSession, *, card_id: int, owner_won_game: bool, new_deadline_at: datetime | None
) -> CelestialBattle:
    """Засчитывает текущую игру победителю, сбрасывает броски и переходит к следующей игре
    (или оставляет `game_index` как есть, если `new_deadline_at` не передан — вызывающий
    сервис уже решил, что матч закончен, финализация — отдельным шагом, см.
    services/celestial._finish_battle)."""
    battle = await session.get(CelestialBattle, card_id)
    assert battle is not None
    if owner_won_game:
        battle.owner_wins += 1
    else:
        battle.challenger_wins += 1
    battle.owner_throw_count = 0
    battle.owner_throw_sum = 0
    battle.challenger_throw_count = 0
    battle.challenger_throw_sum = 0
    battle.game_index += 1
    if new_deadline_at is not None:
        battle.game_deadline_at = new_deadline_at
    await session.flush()
    return battle


async def delete_battle(session: AsyncSession, *, card_id: int) -> None:
    battle = await session.get(CelestialBattle, card_id)
    if battle is not None:
        await session.delete(battle)


async def list_expired_games(session: AsyncSession, *, now: datetime) -> list[CelestialBattle]:
    result = await session.execute(select(CelestialBattle).where(CelestialBattle.game_deadline_at <= now))
    return list(result.scalars().all())
