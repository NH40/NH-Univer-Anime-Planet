from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.game import CASINO_ROLL_COST_COINS
from bot.constant.casino import TRANSACTION_REASON_CASINO_MASS_ROLL, TRANSACTION_REASON_CASINO_ROLL
from bot.db.models.enums import TransactionCurrency
from bot.db.models.transaction import Transaction
from bot.db.repositories.user import spend_coins
from bot.services import ticket
from bot.services.shop import NotEnoughCoinsError

# Списание и начисление награды — намеренно два разных вызова, а не одна функция:
# между ними хендлер должен реально бросить кубик через Telegram (message.answer_dice),
# чтобы узнать значение — это внешний вызов Bot API, ему не место в сервисном слое,
# который работает только с сессией БД. Оба вызова используют одну и ту же сессию без
# промежуточного commit — коммит происходит один раз, в grant_*_reward, уже после того как
# результат броска получен (см. CLAUDE.md, правило 10: списание без результата — недопустимо,
# поэтому если что-то упадёт до commit, откатится и списание тоже).


async def charge_roll(session: AsyncSession, *, user_id: int) -> None:
    """Атомарно списывает стоимость одной крутки. Не коммитит."""
    ok = await spend_coins(session, user_id=user_id, amount=CASINO_ROLL_COST_COINS)
    if not ok:
        raise NotEnoughCoinsError(needed=CASINO_ROLL_COST_COINS)
    session.add(
        Transaction(
            user_id=user_id,
            currency=TransactionCurrency.coins,
            amount=-CASINO_ROLL_COST_COINS,
            reason=TRANSACTION_REASON_CASINO_ROLL,
        )
    )


async def grant_roll_reward(session: AsyncSession, *, user_id: int, roll_value: int) -> None:
    """Начисляет тикеты по выпавшему значению и коммитит всю операцию целиком."""
    await ticket.grant(session, user_id, roll_value)
    session.add(
        Transaction(
            user_id=user_id,
            currency=TransactionCurrency.tickets,
            amount=roll_value,
            reason=TRANSACTION_REASON_CASINO_ROLL,
        )
    )
    await session.commit()


async def charge_mass_roll(session: AsyncSession, *, user_id: int, quantity: int) -> int:
    """Атомарно списывает стоимость `quantity` круток разом. Возвращает списанную сумму.
    Не коммитит — см. charge_roll."""
    cost = quantity * CASINO_ROLL_COST_COINS
    ok = await spend_coins(session, user_id=user_id, amount=cost)
    if not ok:
        raise NotEnoughCoinsError(needed=cost)
    session.add(
        Transaction(
            user_id=user_id,
            currency=TransactionCurrency.coins,
            amount=-cost,
            reason=TRANSACTION_REASON_CASINO_MASS_ROLL,
        )
    )
    return cost


async def grant_mass_roll_reward(session: AsyncSession, *, user_id: int, total_value: int) -> None:
    """Начисляет суммарные тикеты за все крутки масс-крутки и коммитит операцию целиком."""
    await ticket.grant(session, user_id, total_value)
    session.add(
        Transaction(
            user_id=user_id,
            currency=TransactionCurrency.tickets,
            amount=total_value,
            reason=TRANSACTION_REASON_CASINO_MASS_ROLL,
        )
    )
    await session.commit()
