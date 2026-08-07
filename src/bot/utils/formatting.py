from __future__ import annotations

from html import escape


def esc(text: str) -> str:
    """Экранирует пользовательский текст (имя, username и т.п.) перед вставкой в
    HTML-разметку сообщения — бот работает с parse_mode=HTML по умолчанию, поэтому
    непроверенный текст игрока (смена имени и т.д.) обязан проходить через это."""
    return escape(text, quote=False)


def progress_bar(percent: int, *, width: int = 10) -> str:
    """Текстовый прогресс-бар из символов ▓/░ (например, для % собранных карточек
    вселенной в профиле) — percent округляется до ближайшего деления шкалы."""
    percent = max(0, min(100, percent))
    filled = round(width * percent / 100)
    return "▓" * filled + "░" * (width - filled)


_DESCRIPTION_MAX_LENGTH = 600


def description_block(description: str | None, *, fallback: str) -> str:
    """Описание карты — свёрнутая цитата Telegram (`<blockquote expandable>`), игрок сам
    разворачивает, если хочет прочитать (тот же паттерн, что прогресс по вселенным в
    профиле, см. handlers/profile) — длинное описание не растягивает подпись к фото на
    весь экран по умолчанию. Пустое описание — просто fallback, разворачивать нечего.

    Обрезается до `_DESCRIPTION_MAX_LENGTH` — подпись к фото у Telegram ограничена 1024
    символами суммарно (id/имя/вселенная/тир и т.п. тоже туда входят), без обрезки очень
    длинное описание могло бы уронить отправку карточки целиком."""
    if not description:
        return fallback
    text = description if len(description) <= _DESCRIPTION_MAX_LENGTH else description[: _DESCRIPTION_MAX_LENGTH - 1].rstrip() + "…"
    return f"<blockquote expandable>{esc(text)}</blockquote>"


def format_countdown(total_seconds: int) -> str:
    """MM:SS, а часы добавляются спереди (H:MM:SS) только когда больше 59 минут — иначе
    таймер вроде "112:58" (тикеты) или "1439:59" (ежедневный бонус) читается плохо
    (см. запрос пользователя 2026-08-06)."""
    total_seconds = max(0, total_seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"
