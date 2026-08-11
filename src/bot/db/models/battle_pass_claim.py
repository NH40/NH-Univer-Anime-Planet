from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


class BattlePassClaim(Base):
    """Точечные "вне очереди" клеймы уровней Battle Pass (см. CLAUDE.md, "Сезонный пасс:
    клейм произвольной ячейки"). Хранит ТОЛЬКО уровни, забранные С ПРОПУСКОМ более ранних
    (`level > claimed_*_level` в `BattlePass` на момент клейма) — обычный последовательный
    клейм (`level == claimed_*_level + 1`) просто двигает high-water mark в `BattlePass` и
    НЕ создаёт здесь строку (см. `services/battle_pass.claim_level` — "поглощение" цепочки
    подряд идущих строк при продвижении high-water mark). В типичной игре (клеймят по мере
    открытия) эта таблица остаётся почти пустой независимо от числа игроков — сознательный
    компромисс вместо хранения одной строки на КАЖДЫЙ клейм, что на 30k игроков x сотни
    уровней x 2 ветки было бы неприемлемо тяжело для 2GB-сервера (см. CLAUDE.md, "Железо и
    нагрузка")."""

    __tablename__ = "battle_pass_claims"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    season_id: Mapped[int] = mapped_column(Integer, ForeignKey("seasons.id", ondelete="CASCADE"), primary_key=True)
    track: Mapped[str] = mapped_column(String(8), primary_key=True)  # constant.battle_pass.TRACK_FREE/PREMIUM
    level: Mapped[int] = mapped_column(Integer, primary_key=True)
