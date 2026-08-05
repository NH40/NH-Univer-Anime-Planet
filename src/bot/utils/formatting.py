from __future__ import annotations

from html import escape


def esc(text: str) -> str:
    """Экранирует пользовательский текст (имя, username и т.п.) перед вставкой в
    HTML-разметку сообщения — бот работает с parse_mode=HTML по умолчанию, поэтому
    непроверенный текст игрока (смена имени и т.д.) обязан проходить через это."""
    return escape(text, quote=False)
