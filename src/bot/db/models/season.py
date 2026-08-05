from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from bot.db.base import Base


class Season(Base):
    """Игровой сезон. Смена сезона переносит ubp_season игроков в ubp_total и обнуляет
    ubp_season (см. services/season.start_new_season) — award_ubp() трогает только
    ubp_season, ubp_total пополняется ИСКЛЮЧИТЕЛЬНО тут. Смена версии (version) может
    произойти без смены сезона (services/season.bump_version)."""

    __tablename__ = "seasons"
    __table_args__ = (
        # Максимум один активный сезон одновременно — гарантия на уровне БД, тем же
        # паттерном, что и owner/deputy клана (см. db/models/clan.py).
        Index("uq_seasons_active", "is_active", unique=True, postgresql_where="is_active = true"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(16))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
