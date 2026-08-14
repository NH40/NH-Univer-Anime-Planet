from __future__ import annotations

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.game import DUST_DIVISOR, MERGE_COPIES_REQUIRED, dust_for_stars
from bot.constant.dust import TRANSACTION_REASON_DUST
from bot.db.models.enums import TransactionCurrency
from bot.db.models.transaction import Transaction
from bot.db.models.user import User
from bot.db.repositories.card import get_by_id as get_card_by_id
from bot.db.repositories.inventory import decrement_by, decrement_to
from bot.db.repositories.inventory import distill_all_owned as _distill_all_owned_sql


class CardNotFoundError(Exception):
    pass


class NothingToDistillError(Exception):
    """Стопка уже <= целевого количества — распылять нечего (например, keep_one=True
    и там всего одна копия)."""


class NotEnoughCopiesError(Exception):
    """Запрошенное точное количество (distill_amount) превышает то, что реально есть."""

    def __init__(self, needed: int) -> None:
        self.needed = needed


async def _credit_dust(session: AsyncSession, *, user_id: int, reward: int) -> None:
    """Общий хвост всех вариантов распыления: начислить пыль + один audit-ряд в
    transactions. Не коммитит — вызывающая функция коммитит один раз (правило 10)."""
    await session.execute(update(User).where(User.id == user_id).values(dust=User.dust + reward))
    session.add(
        Transaction(user_id=user_id, currency=TransactionCurrency.dust, amount=reward, reason=TRANSACTION_REASON_DUST)
    )


async def distill(
    session: AsyncSession, *, user_id: int, card_id: int, stars: int, keep_one: bool
) -> int:
    """Распыляет дубликаты одной стопки (card_id, stars) в пыль. keep_one=True оставляет
    1 копию (обычное "распылить дубликаты"), False — распыляет всё до нуля ("распылить всё").
    Одна логическая операция — один commit в конце (см. CLAUDE.md, правило 10). Возвращает
    количество начисленной пыли."""
    card = await get_card_by_id(session, card_id)
    if card is None:
        raise CardNotFoundError(card_id)

    target = 1 if keep_one else 0
    dusted = await decrement_to(session, user_id=user_id, card_id=card_id, stars=stars, target=target)
    if dusted is None:
        raise NothingToDistillError

    reward = dusted * dust_for_stars(card.base_ubp, stars)
    await _credit_dust(session, user_id=user_id, reward=reward)

    await session.commit()
    return reward


async def distill_amount(session: AsyncSession, *, user_id: int, card_id: int, stars: int, amount: int) -> int:
    """Распыляет РОВНО `amount` копий стопки (card_id, stars) — точечный ввод (1/5/10/
    своё число, см. handlers/dust). NotEnoughCopiesError, если копий меньше amount (не
    списывает частично). Одна логическая операция — один commit. Возвращает начисленную
    пыль."""
    card = await get_card_by_id(session, card_id)
    if card is None:
        raise CardNotFoundError(card_id)

    ok = await decrement_by(session, user_id=user_id, card_id=card_id, stars=stars, amount=amount)
    if not ok:
        raise NotEnoughCopiesError(needed=amount)

    reward = amount * dust_for_stars(card.base_ubp, stars)
    await _credit_dust(session, user_id=user_id, reward=reward)

    await session.commit()
    return reward


async def distill_all_owned(session: AsyncSession, *, user_id: int, keep_one: bool) -> int:
    """Балк-распыление ВСЕЙ коллекции игрока (все вселенные + ивент-карты) одним атомарным
    SQL-запросом (см. db.repositories.inventory.distill_all_owned) — без Python-цикла по
    стопкам. Квест-метрика "dust_gained" считает СУММУ, не количество строк (см. CLAUDE.md,
    config/quest), поэтому одна Transaction-строка с итогом здесь безопасна. 0 без ошибки,
    если распылять было нечего. Одна логическая операция — один commit."""
    target = 1 if keep_one else 0
    reward = await _distill_all_owned_sql(
        session, user_id=user_id, target=target, divisor=DUST_DIVISOR, copies=MERGE_COPIES_REQUIRED
    )
    if reward:
        await _credit_dust(session, user_id=user_id, reward=reward)
    await session.commit()
    return reward
