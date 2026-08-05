from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


class Card(Base):
    """Мастер-запись карточки (1 звезда, базовый UBP). Наполняется скриптом
    scripts/seed_cards.py из assets/cards/<universe>/<ubp>UBP/<id>_<Name>.<ext>."""

    __tablename__ = "cards"
    __table_args__ = (
        UniqueConstraint("universe_code", "external_id", name="uq_cards_universe_external_id"),
        Index("ix_cards_universe_base_ubp", "universe_code", "base_ubp"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    universe_code: Mapped[str] = mapped_column(ForeignKey("universes.code", ondelete="RESTRICT"))
    external_id: Mapped[str] = mapped_column(String(8))  # "001" из имени файла
    name: Mapped[str] = mapped_column(String(64))
    base_ubp: Mapped[int] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_path: Mapped[str] = mapped_column(String(255))
