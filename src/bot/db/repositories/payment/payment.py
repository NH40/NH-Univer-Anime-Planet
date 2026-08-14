from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.enums import PaymentItemKind, PaymentStatus
from bot.db.models.payment import Payment


async def create_succeeded(
    session: AsyncSession,
    *,
    telegram_payment_charge_id: str,
    user_id: int,
    amount_rub: int,
    item_kind: PaymentItemKind,
    coins_amount: int | None = None,
) -> bool:
    """Атомарный insert — False, если `telegram_payment_charge_id` уже есть (Telegram
    повторно доставил апдейт `successful_payment`) — тогда это не ошибка, просто сигнал
    вызывающему не начислять награду повторно (см. CLAUDE.md, "Донат"/"Магазин: слот капа
    тикетов"). `coins_amount` — только для item_kind=donate_coins, иначе NULL (не 0, см.
    db/models/payment.py). Не коммитит — часть составной операции credit_payment/
    credit_ticket_cap_purchase."""
    stmt = (
        pg_insert(Payment)
        .values(
            telegram_payment_charge_id=telegram_payment_charge_id,
            user_id=user_id,
            amount_rub=amount_rub,
            coins_amount=coins_amount,
            item_kind=item_kind,
            status=PaymentStatus.succeeded,
        )
        .on_conflict_do_nothing(index_elements=[Payment.telegram_payment_charge_id])
        .returning(Payment.id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def get_totals(session: AsyncSession) -> tuple[int, int]:
    """(сумма рублей, число платежей) по успешным платежам за всё время — для /admin статистики."""
    result = await session.execute(
        select(func.coalesce(func.sum(Payment.amount_rub), 0), func.count(Payment.id)).where(
            Payment.status == PaymentStatus.succeeded
        )
    )
    return result.one()
