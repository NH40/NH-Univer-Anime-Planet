from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


class CelestialBattle(Base):
    """Активный бой за небесную карту — ровно один на карту одновременно, `card_id` как PK
    даёт эту гарантию бесплатно (второй бой за ту же карту физически не вставится, пока
    этот не завершён и не удалён, см. CLAUDE.md, "Небесные карты"). Создаётся, когда
    владелец ПРИНИМАЕТ вызов претендента (не при самой заявке — до этого достаточно
    `CelestialOwnership.challenger_id`).

    3 игры фиксируются СРАЗУ при создании боя (`game_1..3`, случайно из
    `RELIC_BATTLE_GAME_POOL`) — не выбираются заново перед каждой игрой, чтобы весь матч был
    предсказуем и претендент/владелец видели вперёд, что их ждёт. `game_index` (0..2) —
    какая из трёх сейчас активна.

    Throws считаем только суммой и количеством, не историей значений (`owner_throw_sum`/
    `owner_throw_count`) — отдельные броски игроку показываются сразу через
    `message.answer_dice()` в момент броска, хранить их для восстановления UI не нужно,
    только для решения "кто выиграл игру" достаточно суммы и факта завершённости (3/3).

    `game_deadline_at` — дедлайн ТЕКУЩЕЙ игры (1ч с момента её начала, см. CLAUDE.md), не
    всего боя целиком — обновляется на новый +1ч при переходе к следующей игре
    (services/celestial._advance_game). Просроченная игра засчитывается тем, кто не успел
    бросить все 3 раза (сравнение throw_count, см. services/celestial._resolve_timed_out_game)."""

    __tablename__ = "celestial_battles"

    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    challenger_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))

    game_1: Mapped[str] = mapped_column(String(16))
    game_2: Mapped[str] = mapped_column(String(16))
    game_3: Mapped[str] = mapped_column(String(16))
    game_index: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")

    owner_wins: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    challenger_wins: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")

    owner_throw_count: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    owner_throw_sum: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    challenger_throw_count: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    challenger_throw_sum: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")

    game_deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
