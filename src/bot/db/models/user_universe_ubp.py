from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


class UserUniverseUbp(Base):
    """UBP игрока в разрезе ОДНОЙ вселенной — отдельно от общего `User.ubp_season`/
    `ubp_total` (см. CLAUDE.md, "Топ по вселенной"). Начисляется ТЕМ ЖЕ событием, что и
    общий UBP (крутка/слияние, см. `services/ubp.award_ubp`), просто дополнительно, в
    разрезе `Card.universe_code` конкретной карты — общий счётчик игрока НЕ заменяется,
    оба растут параллельно из одного и того же начисления.

    Тот же жизненный цикл сезона, что у `User.ubp_season`/`ubp_total`: `ubp_season`
    обнуляется и переносится в `ubp_total` при смене сезона (см.
    `services/season.start_new_season`), не при каждом начислении.

    Составной PK — по строке на каждую вселенную, в которой игрок хоть раз получил UBP
    (не создаётся заранее для всех вселенных разом)."""

    __tablename__ = "user_universe_ubp"
    __table_args__ = (
        Index("ix_user_universe_ubp_universe_season", "universe_code", "ubp_season"),
        Index("ix_user_universe_ubp_universe_total", "universe_code", "ubp_total"),
    )

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    universe_code: Mapped[str] = mapped_column(ForeignKey("universes.code", ondelete="CASCADE"), primary_key=True)
    ubp_season: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    ubp_total: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
