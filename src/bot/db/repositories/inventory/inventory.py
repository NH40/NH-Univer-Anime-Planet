from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import case, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.card import Card
from bot.db.models.inventory import UserCard


async def add_card(session: AsyncSession, *, user_id: int, card_id: int, stars: int, qty: int = 1) -> int:
    """Апсерт по (user_id, card_id, stars): новая строка с quantity=qty, либо
    quantity += qty если строка уже есть (в том числе если раньше распылили в 0 —
    строка не удаляется, см. `db.repositories.card.get_discovered_card_ids`). Не коммитит —
    вызывающий сервис коммитит один раз в конце композитной операции.

    Возвращает итоговое количество копий после апсерта — бесплатно, тем же RETURNING,
    без отдельного SELECT (нужно для "Количество" в подписи к выпавшей карте)."""
    stmt = (
        pg_insert(UserCard)
        .values(user_id=user_id, card_id=card_id, stars=stars, quantity=qty)
        .on_conflict_do_update(
            index_elements=[UserCard.user_id, UserCard.card_id, UserCard.stars],
            set_={"quantity": UserCard.quantity + qty},
        )
        .returning(UserCard.quantity)
    )
    result = await session.execute(stmt)
    return result.scalar_one()


@dataclass
class OwnedStack:
    card: Card
    stars: int
    quantity: int


async def list_owned_stacks_in_tier(
    session: AsyncSession, *, user_id: int, universe_code: str, base_ubp: int
) -> list[OwnedStack]:
    """Все стопки игрока (карта, звезда) с quantity > 0 в этом UBP-тире вселенной,
    отсортированные по id карты, затем по звезде. Одна и та же карта на разных звёздах
    (например, остались 1★ дубли и уже смёржена 2★) — это две отдельные стопки, каждая
    доступна для распыления/слияния независимо. Список принципиально небольшой (инвентарь
    одного игрока в одном тире), поэтому без пагинации на уровне SQL — см. правило 7,
    оно про большие общие списки, а не про срез одного игрока."""
    result = await session.execute(
        select(Card, UserCard.stars, UserCard.quantity)
        .join(UserCard, UserCard.card_id == Card.id)
        .where(
            Card.universe_code == universe_code,
            Card.base_ubp == base_ubp,
            UserCard.user_id == user_id,
            UserCard.quantity > 0,
        )
        .order_by(Card.external_id, UserCard.stars)
    )
    return [OwnedStack(card=card, stars=stars, quantity=qty) for card, stars, qty in result.all()]


async def list_owned_universes(session: AsyncSession, user_id: int) -> list[tuple[str, str]]:
    """(код, название) вселенных, где у игрока есть хотя бы одна карта (quantity > 0) —
    для Mini App (см. TODO, Этап 12): в отличие от `User.universe_selected` (одна текущая
    вселенная для крутки), коллекция может охватывать несколько вселенных сразу, если
    игрок переключался между ними. Джойним Universe сразу, а не отдельным запросом за
    названиями (правило 3) — локальный импорт из-за кросс-доменной модели."""
    from bot.db.models.universe import Universe

    result = await session.execute(
        select(Card.universe_code, Universe.title)
        .join(UserCard, UserCard.card_id == Card.id)
        .join(Universe, Universe.code == Card.universe_code)
        .where(UserCard.user_id == user_id, UserCard.quantity > 0)
        .distinct()
        .order_by(Universe.title)
    )
    return [(code, title) for code, title in result.all()]


async def list_owned_stacks_in_universe(session: AsyncSession, *, user_id: int, universe_code: str) -> list[OwnedStack]:
    """Как list_owned_stacks_in_tier, но без фильтра по тиру — вся коллекция игрока в
    вселенной разом (для Mini App, где нет постраничной навигации бота по тирам)."""
    result = await session.execute(
        select(Card, UserCard.stars, UserCard.quantity)
        .join(UserCard, UserCard.card_id == Card.id)
        .where(Card.universe_code == universe_code, UserCard.user_id == user_id, UserCard.quantity > 0)
        .order_by(Card.base_ubp.desc(), Card.external_id, UserCard.stars)
    )
    return [OwnedStack(card=card, stars=stars, quantity=qty) for card, stars, qty in result.all()]


@dataclass
class UniverseProgress:
    code: str
    title: str
    owned: int
    total: int

    @property
    def percent(self) -> int:
        return round(100 * self.owned / self.total) if self.total else 0


async def get_universe_progress(session: AsyncSession, user_id: int) -> list[UniverseProgress]:
    """Живая агрегация (не денормализованная колонка — тот же принцип, что и UBP клана,
    см. CLAUDE.md): для каждой вселенной — сколько УНИКАЛЬНЫХ персонажей у игрока есть
    хотя бы 1 копия, из скольких существует всего. LEFT JOIN, чтобы вселенные без единой
    карты игрока тоже попали в список (owned=0), а не выпали из GROUP BY."""
    from bot.db.models.universe import Universe

    owned_card_id = case((UserCard.quantity > 0, Card.id), else_=None)
    result = await session.execute(
        select(
            Universe.code,
            Universe.title,
            func.count(func.distinct(owned_card_id)),
            func.count(func.distinct(Card.id)),
        )
        .select_from(Universe)
        .join(Card, Card.universe_code == Universe.code)
        .outerjoin(UserCard, (UserCard.card_id == Card.id) & (UserCard.user_id == user_id))
        .group_by(Universe.code, Universe.title)
        .order_by(Universe.title)
    )
    return [
        UniverseProgress(code=code, title=title, owned=owned, total=total)
        for code, title, owned, total in result.all()
    ]


async def decrement_by(session: AsyncSession, *, user_id: int, card_id: int, stars: int, amount: int) -> bool:
    """Атомарно списывает `amount` из стопки, только если хватает. True — списали,
    False — не хватило (ничего не изменилось). Не коммитит."""
    result = await session.execute(
        text(
            """
            UPDATE user_cards
            SET quantity = quantity - :amount
            WHERE user_id = :user_id AND card_id = :card_id AND stars = :stars AND quantity >= :amount
            RETURNING quantity
            """
        ),
        {"user_id": user_id, "card_id": card_id, "stars": stars, "amount": amount},
    )
    return result.scalar_one_or_none() is not None


_DECREMENT_TO_TARGET_SQL = text(
    """
    WITH cur AS (
        SELECT quantity FROM user_cards
        WHERE user_id = :user_id AND card_id = :card_id AND stars = :stars
        FOR UPDATE
    )
    UPDATE user_cards
    SET quantity = :target
    FROM cur
    WHERE user_cards.user_id = :user_id AND user_cards.card_id = :card_id AND user_cards.stars = :stars
      AND cur.quantity > :target
    RETURNING cur.quantity - :target
    """
)


async def decrement_to(
    session: AsyncSession, *, user_id: int, card_id: int, stars: int, target: int
) -> int | None:
    """Атомарно опускает quantity до `target` (не поднимает). Возвращает, сколько именно
    списали, либо None, если сейчас уже <= target (списывать нечего). Используется
    распылением, где нужно точное количество списанного, чтобы начислить пыль. Не коммитит."""
    result = await session.execute(
        _DECREMENT_TO_TARGET_SQL,
        {"user_id": user_id, "card_id": card_id, "stars": stars, "target": target},
    )
    return result.scalar_one_or_none()
