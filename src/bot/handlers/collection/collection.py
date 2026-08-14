from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InputMediaPhoto
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.game import EVENT_CARD_UBP, ubp_for_stars
from bot.constant.collection import CB_COLL_EVENTS, CB_COLL_NAV_PREFIX, CB_COLL_TIER_PREFIX
from bot.constant.deck import CB_DECK_COLLECTION
from bot.db.repositories.inventory import OwnedStack, list_owned_stacks_in_event_universes, list_owned_stacks_in_tier
from bot.db.repositories.universe import get_by_code as get_universe
from bot.db.repositories.user import get_by_id
from bot.keyboards.collection import stack_view, tier_picker
from bot.texts.collection import EMPTY_TIER, NO_DESCRIPTION, STACK_CAPTION, TIER_PICKER_HEADER
from bot.texts.common import NEED_START
from bot.texts.deck import NO_UNIVERSE_SELECTED
from bot.utils.card_media import cache_card_photo, get_card_photo
from bot.utils.formatting import description_block, esc
from bot.utils.safe_edit import safe_edit_media, safe_edit_text

router = Router(name="collection")


async def _stacks(session: AsyncSession, user_id: int, universe_code: str | None, tier: int) -> list[OwnedStack]:
    """`tier == EVENT_CARD_UBP` — особая категория "Ивенты": карточки из ВСЕХ ивентовых
    вселенных разом, `universe_code` в этом случае не используется (см. CLAUDE.md,
    "Ивенты") — 7000 UBP не входит в TIER_CHANCE_PERCENT, так что коллизий с обычными
    тирами нет, и это значение безопасно "протекает" через тот же tier-based callback_data
    (nav), что и обычные тиры, без отдельной ветки в каждом хендлере ниже."""
    if tier == EVENT_CARD_UBP:
        return await list_owned_stacks_in_event_universes(session, user_id)
    return await list_owned_stacks_in_tier(session, user_id=user_id, universe_code=universe_code, base_ubp=tier)


def _stack_caption(stack: OwnedStack, index: int, total: int) -> str:
    return STACK_CAPTION.format(
        external_id=esc(stack.card.external_id),
        name=esc(stack.card.name),
        stars="🌟" * stack.stars,
        ubp=ubp_for_stars(stack.card.base_ubp, stack.stars),
        quantity=stack.quantity,
        description=description_block(stack.card.description, fallback=NO_DESCRIPTION),
        position=index + 1,
        total=total,
    )


def _parse_tier_index(data: str, prefix: str) -> tuple[int, int]:
    tier_s, index_s = data[len(prefix) :].split(":")
    return int(tier_s), int(index_s)


@router.callback_query(F.data == CB_DECK_COLLECTION)
async def cb_open_collection(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_by_id(session, callback.from_user.id)
    if user is None:
        await callback.answer()
        await callback.message.answer(NEED_START)
        return
    if user.universe_selected is None:
        await callback.answer(NO_UNIVERSE_SELECTED, show_alert=True)
        return

    universe = await get_universe(session, user.universe_selected)
    await callback.answer()
    # Открываем из текстового экрана "Колода" — тоже текст, можно редактировать на месте.
    await safe_edit_text(
        callback.message, TIER_PICKER_HEADER.format(universe=esc(universe.title)), reply_markup=tier_picker()
    )


@router.callback_query(F.data == CB_COLL_EVENTS)
async def cb_open_events(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    user = await get_by_id(session, callback.from_user.id)
    if user is None:
        await callback.answer()
        await callback.message.answer(NEED_START)
        return

    # Не требует user.universe_selected — "Ивенты" не привязаны к текущей выбранной
    # вселенной игрока (см. _stacks).
    stacks = await _stacks(session, callback.from_user.id, None, EVENT_CARD_UBP)
    await callback.answer()
    if not stacks:
        await safe_edit_text(callback.message, EMPTY_TIER, reply_markup=tier_picker())
        return

    photo = await get_card_photo(redis, stacks[0].card)
    sent = await callback.message.answer_photo(
        photo,
        caption=_stack_caption(stacks[0], 0, len(stacks)),
        reply_markup=stack_view(tier=EVENT_CARD_UBP, index=0, total=len(stacks)),
    )
    await cache_card_photo(redis, stacks[0].card.id, sent)


@router.callback_query(F.data.startswith(CB_COLL_TIER_PREFIX))
async def cb_open_tier(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    tier = int(callback.data[len(CB_COLL_TIER_PREFIX) :])
    user = await get_by_id(session, callback.from_user.id)
    if user is None or user.universe_selected is None:
        await callback.answer(NO_UNIVERSE_SELECTED, show_alert=True)
        return

    stacks = await _stacks(session, callback.from_user.id, user.universe_selected, tier)
    await callback.answer()
    if not stacks:
        # Источник — тир-пикер, тоже текст, поэтому редактируем на месте, а не спамим.
        await safe_edit_text(callback.message, EMPTY_TIER, reply_markup=tier_picker())
        return

    # Тир-пикер — текст, карточка — фото, редактировать на месте нельзя (разные типы
    # контента у Telegram), поэтому новое сообщение.
    photo = await get_card_photo(redis, stacks[0].card)
    sent = await callback.message.answer_photo(
        photo,
        caption=_stack_caption(stacks[0], 0, len(stacks)),
        reply_markup=stack_view(tier=tier, index=0, total=len(stacks)),
    )
    await cache_card_photo(redis, stacks[0].card.id, sent)


@router.callback_query(F.data.startswith(CB_COLL_NAV_PREFIX))
async def cb_navigate(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    tier, index = _parse_tier_index(callback.data, CB_COLL_NAV_PREFIX)
    user = await get_by_id(session, callback.from_user.id)
    if user is None or (tier != EVENT_CARD_UBP and user.universe_selected is None):
        await callback.answer(NO_UNIVERSE_SELECTED, show_alert=True)
        return

    stacks = await _stacks(session, callback.from_user.id, user.universe_selected, tier)
    await callback.answer()
    if not stacks:
        await callback.message.answer(EMPTY_TIER, reply_markup=tier_picker())
        return

    index = max(0, min(index, len(stacks) - 1))
    stack = stacks[index]
    photo = await get_card_photo(redis, stack.card)
    edited = await safe_edit_media(
        callback.message,
        InputMediaPhoto(media=photo, caption=_stack_caption(stack, index, len(stacks))),
        reply_markup=stack_view(tier=tier, index=index, total=len(stacks)),
    )
    if edited is not None:
        await cache_card_photo(redis, stack.card.id, edited)
