from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from bot.db.base import Base


class SbpPayment(Base):
    """Счёт на оплату по СБП через API ЮKassa (2026-10-30). Зачисление коинов — тот же
    `services/donate.credit_payment`, что у оплаты картой; идемпотентность — переход
    `status` в succeeded одним UPDATE плюс unique `payments.telegram_payment_charge_id`
    (сюда пишется `yk:<id платежа>`)."""

    __tablename__ = "sbp_payments"
    __table_args__ = (Index("ix_sbp_payments_status_created", "status", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    yookassa_id: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    amount_rub: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16))  # constant/donate.SBP_STATUS_*
    confirmation_url: Mapped[str] = mapped_column(Text)
    # Сообщение со счётом — после оплаты с него снимаются кнопки.
    chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
