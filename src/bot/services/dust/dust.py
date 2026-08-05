from __future__ import annotations

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.game import dust_for_stars
from bot.constant.dust import TRANSACTION_REASON_DUST
from bot.db.models.enums import TransactionCurrency
from bot.db.models.transaction import Transaction
from bot.db.models.user import User
from bot.db.repositories.card import get_by_id as get_card_by_id
from bot.db.repositories.inventory import decrement_to


class CardNotFoundError(Exception):
    pass


class NothingToDistillError(Exception):
    """Стопка уже <= целевого количества — распылять нечего (например, keep_one=True
    и там всего одна копия)."""


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

    await session.execute(update(User).where(User.id == user_id).values(dust=User.dust + reward))
    session.add(
        Transaction(user_id=user_id, currency=TransactionCurrency.dust, amount=reward, reason=TRANSACTION_REASON_DUST)
    )

    await session.commit()
    return reward
