from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from bot.db.base import Base


class User(Base):
    """Игрок. `id` — это Telegram user id (не суррогатный ключ), чтобы не плодить лишний join
    на каждый хендлер."""

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_clan_id", "clan_id"),
        Index("ix_users_ubp_season", "ubp_season"),
        Index("ix_users_referred_by_id", "referred_by_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(32), nullable=True)

    universe_selected: Mapped[str | None] = mapped_column(
        ForeignKey("universes.code", ondelete="SET NULL"), nullable=True
    )
    # use_alter=True — разрывает цикл users.clan_id -> clans.id / clans.owner_id -> users.id
    # для DDL: без этого alembic не может определить порядок CREATE TABLE (см. SAWarning
    # "Cannot correctly sort tables... cycles between tables clans, users") и создаёт clans
    # раньше users, что падает на FK clans.owner_id -> users. С use_alter FK на clan_id
    # добавляется отдельным ALTER TABLE уже после того, как обе таблицы существуют.
    clan_id: Mapped[int | None] = mapped_column(
        ForeignKey("clans.id", ondelete="SET NULL", use_alter=True), nullable=True
    )
    # Кто пригласил этого игрока по персональной реферальной ссылке (t.me/<bot>?start=r_<id>,
    # см. handlers/start) — выставляется один раз при первом /start по такой ссылке
    # (db/repositories/user: set_referred_by, WHERE referred_by_id IS NULL), дальше не
    # меняется. Отдельно от ReferralLink/ReferralVisit (db/models/referral.py) — те под
    # именные кампании админа (см. CLAUDE.md, Этап 10), не под личные ссылки игроков.
    referred_by_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # Доп. админы сверх ADMIN_IDS из .env (см. CLAUDE.md, "Админ-панель") — обычный флаг,
    # без отдельной таблицы: выдать/забрать можно одним UPDATE по username.
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # Игровая валюта — источник правды здесь, в Postgres. Redis используется как кэш
    # только для лидерборда и локов от повторных кликов; тикеты читаются/пишутся
    # напрямую в Postgres — см. CLAUDE.md, "Модель тикетов".
    ubp_season: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    ubp_total: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    dust: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    # Донатная валюта, покупается за рубли через ЮKassa 1:1 (см. CLAUDE.md, "Донат").
    coins: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")

    # Integer, а не SmallInteger — тикеты можно докупать за коины/промокоды сверх
    # "естественного" капа регена (см. CLAUDE.md, "Модель тикетов"), сумма не должна
    # рисковать переполнением smallint.
    tickets_count: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
    tickets_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Накопительный счётчик — сколько карт всего выбито круткой (x1+x10), для профиля.
    total_rolls: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")

    # Истекает в будущем = активна. NULL/в прошлом = нет активной. Каждая покупка "стакает"
    # дни поверх текущего истечения — см. CLAUDE.md/TODO.md, "Магазин коинов". Пока активна —
    # ускоряет тикет-реген (см. config/game: TICKET_REGEN_INTERVAL_SECONDS_SUBSCRIBED) и даёт
    # +5 тикетов раз в 24ч (см. services/notify), см. CLAUDE.md, "Подписка".
    subscription_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Якорь для суточного начисления тикетов подпиской — NULL, пока ни разу не подписывался;
    # выставляется один раз при первой покупке подписки (см. db/repositories/user:
    # extend_subscription), дальше двигается фоновым шедулером на каждые списанные 24ч.
    subscription_ticket_granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Отдельно от полноценного Battle Pass (таблица battle_passes, per-season) — это только
    # флаг/срок premium-доступа, сам Battle Pass ещё не спроектирован (см. TODO, Этап 8).
    premium_pass_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Отдельные тумблеры уведомлений (Настройки -> Уведомления) — не переиспользуют общий
    # notifications_enabled (тот теперь только про обменник пыли в клане, см. handlers/clan).
    notify_tickets_full: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    notify_roll_reminder: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # Уведомления "заявка в клан"/"приглашение в клан" — обе стороны, где получатель потом
    # соглашается или отказывает (см. CLAUDE.md, "Кланы"). Подтверждено пользователем
    # 2026-08-05 — отдельный тумблер, не тот же notifications_enabled.
    notify_clan_requests: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # Якорь для напоминания "пора крутить" раз в 12ч (см. services/notify) — server_default,
    # чтобы первое напоминание пришло через 12ч ПОСЛЕ регистрации, а не сразу же.
    roll_reminder_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Ежедневный бонус (см. CLAUDE.md, "Ежедневный бонус") — streak 1..7,
    # services/daily_bonus.claim: заберёт в течение 24-48ч с прошлого раза -> +1 (макс 7);
    # пропустил день (>48ч) -> сброс на 1 при следующем сборе. claimed_at=NULL — ни разу
    # не забирал, следующий сбор — день 1.
    daily_bonus_streak: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    daily_bonus_claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notify_daily_bonus: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # Отдельный якорь для пуша "бонус готов" (services/notify) — НЕ переиспользует
    # daily_bonus_claimed_at (тронуть его означало бы исказить логику claim() выше).
    # Сравнивается с daily_bonus_claimed_at: notified_at < claimed_at значит "ещё не
    # уведомляли про ТЕКУЩЕЕ окно готовности" — естественно сбрасывается каждым новым claim.
    daily_bonus_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Ежедневные задания (см. CLAUDE.md, "Ежедневные задания") — сами 5 активных заданий
    # лежат в таблице `daily_quests` (db/models/quest.py), здесь — только якоря и счётчики
    # рероллов, которые сбрасываются вместе с обновлением набора. quests_refreshed_at —
    # реальный игровой якорь (обновляется ТОЛЬКО когда набор фактически переигран, лениво
    # при заходе на экран после 24ч, см. services/quest/quest.py). quests_notified_at —
    # ОТДЕЛЬНЫЙ якорь для пуша "задания обновлены" (services/notify), не трогает
    # quests_refreshed_at — тот же анти-порча приём, что и у daily_bonus_notified_at выше.
    quests_refreshed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    quests_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notify_daily_quests: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # 1 "переролл всех" в сутки (флаг, сбрасывается в False при каждом обновлении набора) +
    # 2 переролла ОТДЕЛЬНОГО задания в сутки (счётчик, сбрасывается в 0 вместе с флагом).
    daily_quest_reroll_all_used: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    daily_quest_individual_reroll_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # "Онлайн" в статистике /admin = активны за последние 24ч. Обновляется одним UPDATE
    # внутри BanCheckMiddleware на каждый апдейт (тот же запрос, что и бан-чек, не второй
    # сверху, см. CLAUDE.md, правило 4 — единичный indexed UPDATE по PK дёшев на 30k онлайн).
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
