from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


class CelestialHistory(Base):
    """Игрок когда-либо ВЛАДЕЛ этой небесной картой, но уже не владеет — для псевдо-
    божественной карты (см. CLAUDE.md, "Небесные карты"). Ставится ТОЛЬКО в момент потери
    карты (проигрыш боя, таймаут решения или явный отказ), не при получении — текущее
    владение и так учтено через `CelestialOwnership.owner_id`; псевдо-божественная
    проверяет объединение "текущий владелец" + "эта таблица" (см.
    services/celestial.check_pseudo_divine), поэтому нет смысла писать сюда же владение,
    которое ещё не потеряно.

    Составной PK — по определению не повторяется на одного игрока/карту (повторная потеря
    той же карты тем же игроком просто не меняет уже существующую строку)."""

    __tablename__ = "celestial_history"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True)
