from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.game import DONATE_COINS_PER_RUB, REFERRAL_DONATE_CUT_PERCENT
from bot.constant.donate import TRANSACTION_REASON_DONATE
from bot.constant.referral import TRANSACTION_REASON_REFERRAL_DONATE_CUT
from bot.db.models.enums import PaymentItemKind, TransactionCurrency
from bot.db.models.transaction import Transaction
from bot.db.repositories import payment as payment_repo
from bot.db.repositories.user import add_coins, get_by_id


async def credit_payment(
    session: AsyncSession, *, telegram_payment_charge_id: str, user_id: int, amount_rub: int
) -> int | None:
    """Начисляет коины за успешный платёж. Возвращает начисленное количество коинов, или
    None, если этот платёж уже был обработан раньше (Telegram может повторно доставить
    апдейт `successful_payment` — деньги списаны Telegram один раз, но апдейт может
    прилететь дважды). Идемпотентность — через unique(`telegram_payment_charge_id`) в
    `payments`, не через Redis-лок: лок защищает от повторного КЛИКА игрока, а здесь
    источник повторов — сервер Telegram, а не UI (см. CLAUDE.md, "Донат").

    Заодно — если у игрока есть реферер (`User.referred_by_id`), тому начисляется
    REFERRAL_DONATE_CUT_PERCENT% от начисленных коинов (округление вниз), пока действует
    связь (см. CLAUDE.md, "Рефералы") — тем же commit'ом, идемпотентность уже гарантирована
    проверкой выше (повторная доставка апдейта просто не дойдёт до этого места второй раз)."""
    coins = amount_rub * DONATE_COINS_PER_RUB

    ok = await payment_repo.create_succeeded(
        session,
        telegram_payment_charge_id=telegram_payment_charge_id,
        user_id=user_id,
        amount_rub=amount_rub,
        item_kind=PaymentItemKind.donate_coins,
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

    payer = await get_by_id(session, user_id)
    if payer is not None and payer.referred_by_id is not None:
        cut = coins * REFERRAL_DONATE_CUT_PERCENT // 100
        if cut > 0:
            await add_coins(session, user_id=payer.referred_by_id, amount=cut)
            session.add(
                Transaction(
                    user_id=payer.referred_by_id,
                    currency=TransactionCurrency.coins,
                    amount=cut,
                    reason=TRANSACTION_REASON_REFERRAL_DONATE_CUT,
                )
            )

    await session.commit()
    return coins
