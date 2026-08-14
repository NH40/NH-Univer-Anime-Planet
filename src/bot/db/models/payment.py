from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from bot.db.base import Base
from bot.db.models.enums import PaymentItemKind, PaymentStatus


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # Идемпотентность по id платежа от Telegram (из Message.successful_payment), а не по
    # внешнему id ЮKassa — Telegram может повторно доставить апдейт, и именно этот id
    # не даст зачислить коины дважды за одну оплату (см. CLAUDE.md, "Донат").
    telegram_payment_charge_id: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    amount_rub: Mapped[int] = mapped_column(Integer)
    # Nullable — заполняется только для item_kind=donate_coins (см. CLAUDE.md, "Магазин:
    # слот капа тикетов"); покупки, не конвертируемые в коины, оставляют это поле пустым, а
    # не 0 (0 неотличим от "начислили ноль коинов" по ошибке).
    coins_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    item_kind: Mapped[PaymentItemKind] = mapped_column(
        Enum(PaymentItemKind, name="payment_item_kind"),
        default=PaymentItemKind.donate_coins,
        server_default=PaymentItemKind.donate_coins.value,
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status"), default=PaymentStatus.pending
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
