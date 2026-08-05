from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Единая точка конфигурации бота. Читается из переменных окружения / .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str
    # alias, т.к. в .env переменная называется ADMIN_IDS (без _raw)
    admin_ids_raw: str = Field(default="", alias="ADMIN_IDS")

    database_url: str
    redis_url: str

    # provider_token из BotFather (Bot Settings -> Payments -> ЮKassa), не ключи с сайта
    # ЮKassa напрямую — оплата идёт через sendInvoice/pre_checkout_query, без отдельного
    # вебхука от ЮKassa (см. CLAUDE.md, "Донат").
    yookassa_provider_token: str = ""

    log_level: str = "INFO"
    tz: str = "Europe/Moscow"

    # Путь к датасетам карточек (см. CLAUDE.md, "Формат карточек") — относительно cwd
    # процесса. В Docker WORKDIR=/app и assets/cards смонтирован как /app/assets/cards.
    cards_dir: str = "assets/cards"

    # URL Mini App (см. TODO, Этап 12) — пусто, пока нет домена/HTTPS: кнопка запуска
    # в главном меню тогда просто не показывается, а не ведёт на битую ссылку.
    mini_app_url: str = ""

    # Пул соединений Postgres — держим маленьким, сервер 2GB RAM.
    db_pool_size: int = 5
    db_max_overflow: int = 5

    # Общий антифлуд (см. middlewares/throttling.py) — минимальный интервал между
    # апдейтами одного игрока. Не игровой баланс (правило 8 про config/game — это шансы/
    # лимиты/формулы), инженерная настройка инфраструктуры — поэтому в Settings, не там.
    throttle_interval_ms: int = 400

    @property
    def admin_ids(self) -> set[int]:
        return {int(x) for x in self.admin_ids_raw.split(",") if x.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
