from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

from bot.texts.common import BTN_CLAN, BTN_COLLECTION_APP, BTN_DECK, BTN_DONATE, BTN_PASS, BTN_PROFILE, BTN_SHOP


def main_menu(*, mini_app_url: str | None = None) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=BTN_PROFILE), KeyboardButton(text=BTN_DECK)],
        [KeyboardButton(text=BTN_SHOP), KeyboardButton(text=BTN_CLAN)],
        [KeyboardButton(text=BTN_PASS), KeyboardButton(text=BTN_DONATE)],
    ]
    if mini_app_url:
        # Кнопка есть только когда есть домен/HTTPS (см. TODO, Этап 12) — иначе она вела
        # бы на несуществующий адрес, Settings.mini_app_url по умолчанию пустая строка.
        rows.append([KeyboardButton(text=BTN_COLLECTION_APP, web_app=WebAppInfo(url=mini_app_url))])

    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=True)
