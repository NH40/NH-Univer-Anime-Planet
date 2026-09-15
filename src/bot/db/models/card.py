from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


class Card(Base):
    """Мастер-запись карточки (1 звезда, базовый UBP). Наполняется скриптом
    scripts/seed_cards.py из assets/cards/<universe>/<ubp>UBP/<id>_<Name>.<ext>.

    `is_celestial`/`is_divine` (см. CLAUDE.md, "Небесные карты") — наполняются ОТДЕЛЬНЫМ
    скриптом `scripts/seed_relics.py` из `assets/celestial/celestial.csv` /
    `assets/divine/divine.csv`, не `seed_cards.py` — это редкие вручную описываемые карты
    (10 небесных + по одной божественной на вселенную + одна глобальная), не папки с
    десятками файлов на вселенную. `base_ubp` у них — CELESTIAL_CARD_BASE_UBP/
    DIVINE_CARD_BASE_UBP (config/game), сознательно ВНЕ `TIER_CHANCE_PERCENT` — как и у
    ивент-карт, они не участвуют в обычном взвешенном пикере тиров, только в отдельных
    проверках (services/gacha, services/celestial)."""

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
    is_celestial: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_divine: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # Различают 3 подтипа божественной карты (см. CLAUDE.md, "Небесные карты"), оба флага
    # не используются, если is_divine=False:
    #   is_divine_global=False                       -> "000": за полный сбор обычного
    #       ростера СВОЕЙ вселенной (universe_code — та самая вселенная, по одной на неё).
    #   is_divine_global=True,  is_divine_pseudo=False -> "1000": единственная на весь бот,
    #       за ОДНОВРЕМЕННОЕ владение всеми небесными картами разом.
    #   is_divine_global=True,  is_divine_pseudo=True  -> "псевдо-1000": отдельная, более
    #       слабая карта — за то, что игрок КОГДА-ЛИБО владел всеми небесными, но не
    #       одновременно (подтверждено пользователем 2026-09-15 как ТРЕТЬЯ карта, не то же
    #       самое, что "1000"). Не выдаётся, если "1000" уже получена (та строго сильнее).
    is_divine_global: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_divine_pseudo: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
