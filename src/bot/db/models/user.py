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
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(32), nullable=True)

    universe_selected: Mapped[str | None] = mapped_column(
        ForeignKey("universes.code", ondelete="SET NULL"), nullable=True
    )
    clan_id: Mapped[int | None] = mapped_column(
        ForeignKey("clans.id", ondelete="SET NULL"), nullable=True
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

    # "Онлайн" в статистике /admin = активны за последние 24ч. Обновляется одним UPDATE
    # внутри BanCheckMiddleware на каждый апдейт (тот же запрос, что и бан-чек, не второй
    # сверху, см. CLAUDE.md, правило 4 — единичный indexed UPDATE по PK дёшев на 30k онлайн).
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
