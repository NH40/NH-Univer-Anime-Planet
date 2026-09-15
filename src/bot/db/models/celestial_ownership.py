from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


class CelestialOwnership(Base):
    """Кто сейчас владеет небесной картой — ровно одна строка на каждую из
    CELESTIAL_CARD_COUNT карт (см. CLAUDE.md, "Небесные карты"), создаётся при ПЕРВОМ
    выпадении карты кому-либо (services/celestial.handle_drop) — до этого владельца просто
    нет, карта может выпасть любому игроку.

    `challenger_id` не NULL значит "есть претендент": либо ждём решения владельца
    (`challenge_deadline_at` — дедлайн 6ч, ещё нет строки в `celestial_battles`), либо уже
    идёт бой (строка в `celestial_battles` есть, `challenge_deadline_at` в этом случае не
    актуален — таймингом боя управляет `CelestialBattle.game_deadline_at`). Второй
    претендент одновременно невозможен по правилам игры — это гарантируется в коде
    (services/celestial), а не констрейнтом (претендента можно снять/заменить только через
    разрешение текущего конфликта).

    `owner_id`/`challenger_id` — ondelete=CASCADE: если владелец удаляет аккаунт, вся
    строка удаляется вместе с ним и карта становится снова "непойманной" (свободной для
    нового дропа) — то же самое поведение, что было бы у любой другой единственной в своём
    роде игровой сущности, привязанной к удалённому аккаунту. Если аккаунт удаляет
    ПРЕТЕНДЕНТ во время ожидания решения — `challenger_id` вернётся в NULL, конфликт снят
    автоматически, владелец просто остаётся владельцем."""

    __tablename__ = "celestial_ownerships"

    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    challenger_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    challenge_deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
