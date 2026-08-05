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
