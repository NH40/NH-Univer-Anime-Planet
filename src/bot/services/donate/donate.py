from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.game import DONATE_COINS_PER_RUB
from bot.constant.donate import TRANSACTION_REASON_DONATE
from bot.db.models.enums import TransactionCurrency
from bot.db.models.transaction import Transaction
from bot.db.repositories import payment as payment_repo
from bot.db.repositories.user import add_coins


async def credit_payment(
    session: AsyncSession, *, telegram_payment_charge_id: str, user_id: int, amount_rub: int
) -> int | None:
    """Начисляет коины за успешный платёж. Возвращает начисленное количество коинов, или
    None, если этот платёж уже был обработан раньше (Telegram может повторно доставить
    апдейт `successful_payment` — деньги списаны Telegram один раз, но апдейт может
    прилететь дважды). Идемпотентность — через unique(`telegram_payment_charge_id`) в
    `payments`, не через Redis-лок: лок защищает от повторного КЛИКА игрока, а здесь
    источник повторов — сервер Telegram, а не UI (см. CLAUDE.md, "Донат")."""
    coins = amount_rub * DONATE_COINS_PER_RUB

    ok = await payment_repo.create_succeeded(
        session,
        telegram_payment_charge_id=telegram_payment_charge_id,
        user_id=user_id,
        amount_rub=amount_rub,
        coins_amount=coins,
    )
    if not ok:
        return None

    await add_coins(session, user_id=user_id, amount=coins)
    session.add(
        Transaction(
            user_id=user_id, currency=TransactionCurrency.coins, amount=coins, reason=TRANSACTION_REASON_DONATE
        )
    )
    await session.commit()
    return coins
