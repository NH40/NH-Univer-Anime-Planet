from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from bot.db.base import Base
from bot.db.models.enums import TransactionCurrency


class Transaction(Base):
    """Аудит-лог всех начислений/списаний. Только insert, ничего не обновляется/удаляется."""

    __tablename__ = "transactions"
    __table_args__ = (Index("ix_transactions_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    currency: Mapped[TransactionCurrency] = mapped_column(
        Enum(TransactionCurrency, name="transaction_currency")
    )
    amount: Mapped[int] = mapped_column(BigInteger)  # может быть отрицательным (списание)
    reason: Mapped[str] = mapped_column(String(128))
    admin_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
