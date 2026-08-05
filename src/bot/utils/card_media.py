from __future__ import annotations

from pathlib import Path

from aiogram.types import FSInputFile

from bot.config.settings import get_settings
from bot.db.models.card import Card


def card_photo(card: Card) -> FSInputFile:
    path = Path(get_settings().cards_dir) / card.image_path
    return FSInputFile(path)
