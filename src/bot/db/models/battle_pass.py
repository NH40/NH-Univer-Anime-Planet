from __future__ import annotations

from datetime import date

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


class BattlePass(Base):
    """Прогресс сезонного пасса игрока.

    `progress` (переработано 2026-08-08, см. CLAUDE.md, "Сезонный пасс: 500 циклических
    уровней") — накопительный счётчик, ОТДЕЛЬНЫЙ от `User.ubp_season`: раньше уровень
    считался на лету прямо из `ubp_season` (та же "живая агрегация", что UBP клана), но
    теперь на скорость набора `progress` влияет дневной буст (см. `boost_levels_used_today`
    ниже), который НЕ должен искажать настоящий `ubp_season` (лидерборды/войны кланов) —
    поэтому это персистентная колонка, растёт только через `services/battle_pass.add_progress`.
    Уровень считается из неё через `config/game: battle_pass_level_from_progress`.

    `boost_levels_used_today`/`boost_date` — дневная квота ускоренного набора `progress`
    (первые 5 уровней сегодняшнего прогресса — ×10 к реальному UBP, следующие 5 — ×5,
    следующие 10 — ×2, дальше — без буста). Ленивый дневной сброс: если `boost_date` не
    сегодня, счётчик трактуется как 0 (тот же паттерн, что ежедневный бонус/тикеты) — нет
    отдельного шедулера, обнуление происходит на первом же начислении UBP за новый день.

    `is_premium` — разовый флаг "премиум-ветка ЭТОГО сезона открыта навсегда, раз игрок
    купил Battle Pass" (подтверждено пользователем 2026-08-05/2026-08-06: разовая покупка
    на сезон, без продлений по дням) — выставляется в `services/shop.buy_premium_pass`
    (блокирует повторную покупку, если уже True) и не сбрасывается до смены сезона (новый
    сезон = новая строка с новым `season_id`, PK). `User.premium_pass_until` — более ранний
    неиспользуемый таймер, оставлен в схеме, но ничего больше в него не пишет.

    `claimed_free_level`/`claimed_premium_level` (изменено 2026-08-11, см. CLAUDE.md,
    "Сезонный пасс: клейм произвольной ячейки") — high-water mark ГАРАНТИРОВАННО забранного
    СПЛОШНОГО префикса (1..N без пропусков), не "максимальный когда-либо забранный уровень".
    Тап по конкретной ячейке теперь забирает ТОЛЬКО её награду (см.
    `services/battle_pass.claim_level`); если это следующий по очереди уровень — просто
    двигает эту колонку на 1. Уровни, забранные С ПРОПУСКОМ более ранних, живут в отдельной
    `BattlePassClaim` (см. её docstring) и поглощаются в high-water mark по мере того, как
    пропущенные уровни тоже забираются. Кнопка "Забрать всё" (`claim_all`) по-прежнему
    выдаёт разом весь диапазон `claimed_*_level+1..текущий` и передвигает high-water mark
    до текущего уровня целиком."""

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
    progress: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    boost_levels_used_today: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    boost_date: Mapped[date | None] = mapped_column(Date, nullable=True)
