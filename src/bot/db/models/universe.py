from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


class Universe(Base):
    """Вселенная карточек: onepiece / lookism / genshin / ... Код — папка в assets/cards."""

    __tablename__ = "universes"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # Ивентовая вселенная (см. CLAUDE.md, "Ивенты") — выставляется seed_cards.py по коду
    # папки (см. config/event.EVENT_DEFS). Не участвует в обычном пикере вселенных
    # (db/repositories/universe.list_active) и в обычной крутке (get_tier_map/pick_card
    # её карты просто не видят — там 7000 UBP вне TIER_CHANCE_PERCENT).
    is_event: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
