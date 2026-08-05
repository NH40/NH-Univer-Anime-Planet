from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


class BattlePass(Base):
    """Прогресс сезонного пасса игрока. `level` намеренно НЕ хранится — он считается на
    лету из `User.ubp_season` (см. `config/game: battle_pass_level_from_ubp`), тем же
    паттерном "живая агрегация вместо денормализованной колонки", что и UBP клана (см.
    CLAUDE.md, "Кланы") — не нужно ничего инкрементить при каждом начислении UBP игроку.

    `is_premium` — не срез "подписка активна прямо сейчас" (это `User.premium_pass_until`,
    отдельный, НЕ привязанный к сезону таймер), а разовый флаг "премиум-ветка ЭТОГО сезона
    открыта навсегда, раз игрок хоть раз купил Battle Pass, пока сезон активен" (подтверждено
    пользователем 2026-08-05) — выставляется в `services/shop.buy_premium_pass` и больше не
    сбрасывается до смены сезона (новый сезон = новая строка с новым `season_id`, PK).

    `claimed_free_level`/`claimed_premium_level` — до какого уровня награды уже забраны
    (high-water mark, не набор конкретных уровней) — кнопка "забрать" выдаёт всё сразу от
    `claimed_*_level + 1` до текущего уровня."""

    __tablename__ = "battle_passes"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"), primary_key=True
    )
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    claimed_free_level: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    claimed_premium_level: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
