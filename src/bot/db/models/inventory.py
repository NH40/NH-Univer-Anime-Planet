from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


class UserCard(Base):
    """Инвентарь игрока. Композитный PK (user_id, card_id, stars) — копии одной и той же
    карты одной звёздности хранятся одной строкой со счётчиком quantity, апсертятся
    через `INSERT ... ON CONFLICT DO UPDATE quantity = quantity + 1` (см. CLAUDE.md, правило 3)."""

    __tablename__ = "user_cards"
    __table_args__ = (Index("ix_user_cards_user_id", "user_id"),)

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    card_id: Mapped[int] = mapped_column(
        ForeignKey("cards.id", ondelete="RESTRICT"), primary_key=True
    )
    stars: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)
    quantity: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
