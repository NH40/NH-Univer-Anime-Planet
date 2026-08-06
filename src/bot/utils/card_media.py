from __future__ import annotations

from pathlib import Path

from aiogram.types import FSInputFile, Message
from redis.asyncio import Redis

from bot.cache.keys import card_file_id as card_file_id_key
from bot.config.settings import get_settings
from bot.db.models.card import Card

# file_id остаётся рабочим у Telegram неограниченно долго — TTL здесь не про его
# истечение там, а страховка на случай, если админ заменит картинку на диске для того же
# card_id (переименовал/перезалил арт): кэш сам протухнет и следующая отправка подхватит
# актуальный файл заново, вместо ручной чистки Redis.
CARD_FILE_ID_TTL_SECONDS = 30 * 24 * 60 * 60


async def get_card_photo(redis: Redis, card: Card) -> str | FSInputFile:
    """Фото карточки для отправки/редактирования — Telegram `file_id` из кэша (Telegram
    отдаёт его почти мгновенно, без повторной загрузки байтов картинки), либо локальный
    файл, если карточку ещё ни разу не отправляли (см. CLAUDE.md, "Кэш фото карточек").
    Именно повторная загрузка одного и того же файла в Telegram при каждой отправке —
    узкое место, не сеть до Telegram и не диск. `file_id` появляется только в ответ на
    реальную отправку, поэтому кэшировать его нужно отдельным вызовом после (см.
    `cache_card_photo`), эта функция сама ничего не пишет в Redis."""
    cached = await redis.get(card_file_id_key(card.id))
    if cached:
        return cached
    return FSInputFile(Path(get_settings().cards_dir) / card.image_path)


async def cache_card_photo(redis: Redis, card_id: int, message: Message) -> None:
    """Сохраняет `file_id` из только что отправленного/отредактированного сообщения с
    фото карточки — вызывать после каждой отправки/edit_media, даже если фото пришло уже
    из кэша (лишняя `SET` дёшева, а TTL при этом продлевается для "горячих" карточек)."""
    if not message.photo:
        return
    largest = message.photo[-1]
    await redis.set(card_file_id_key(card_id), largest.file_id, ex=CARD_FILE_ID_TTL_SECONDS)
