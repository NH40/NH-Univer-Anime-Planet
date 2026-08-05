from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.keys import action_lock
from bot.cache.lock import try_acquire
from bot.config.game import TICKET_NATURAL_CAP, TIER_CHANCE_PERCENT
from bot.config.settings import get_settings
from bot.constant.deck import (
    CB_DECK_CHANCES,
    CB_DECK_CHANCES_BACK,
    CB_DECK_CHANCES_TIER_PREFIX,
    CB_DECK_OPEN,
    CB_DECK_ROLL1,
    CB_DECK_ROLL10,
    LOCK_ACTION_ROLL,
)
from bot.db.models.card import Card
from bot.db.models.universe import Universe
from bot.db.repositories.card import get_discovered_card_ids
from bot.db.repositories.universe import get_by_code as get_universe
from bot.db.repositories.user import get_by_id
from bot.keyboards.deck import back_to_deck, chances_menu, chances_tier_menu, deck_menu
from bot.services import ticket
from bot.services.card import UniverseNotReadyError, get_tier_map
from bot.services.gacha import NoActiveSeasonError, NotEnoughTicketsError, RollResult, roll_one, roll_ten
from bot.texts.common import BTN_DECK, NEED_START
from bot.texts.deck import (
    CARD_CAPTION,
    CHANCES_CARD_LINE,
    CHANCES_HEADER,
    CHANCES_TIER_HEADER,
    CHANCES_UNDISCOVERED,
    DECK_SCREEN,
    NO_ACTIVE_SEASON,
    NO_DESCRIPTION,
    NO_UNIVERSE_SELECTED,
    NOT_ENOUGH_TICKETS,
    ROLL_TEN_LINE,
    ROLL_TEN_RESULT_HEADER,
    TIER_EMOJI,
    TIER_NAMES,
    UNIVERSE_NOT_READY,
)
from bot.utils.card_media import card_photo
from bot.utils.formatting import esc
from bot.utils.safe_edit import safe_edit_text

router = Router(name="deck")


def _card_caption(card: Card, stars: int, universe_title: str, quantity: int) -> str:
    return CARD_CAPTION.format(
        external_id=esc(card.external_id),
        name=esc(card.name),
        universe=esc(universe_title),
        ubp=card.base_ubp,
        stars="🌟" * stars,
        quantity=quantity,
        tier_emoji=TIER_EMOJI.get(card.base_ubp, "🏳️"),
        tier_name=TIER_NAMES.get(card.base_ubp, card.base_ubp),
        description=esc(card.description) if card.description else NO_DESCRIPTION,
    )


async def _render_deck(session: AsyncSession, user_id: int) -> tuple[str, object | None]:
    user = await get_by_id(session, user_id)
    if user is None:
        return NEED_START, None
    if user.universe_selected is None:
        return NO_UNIVERSE_SELECTED, None

    universe = await get_universe(session, user.universe_selected)
    tickets = await ticket.get_balance(session, user_id)
    await session.commit()  # get_balance могла применить лениво накопленный реген

    text = DECK_SCREEN.format(
        universe=esc(universe.title), tickets=tickets, cap=TICKET_NATURAL_CAP, dust=user.dust
    )
    settings = get_settings()
    return text, deck_menu(mini_app_url=settings.mini_app_url or None)


@router.message(Command("deck"))
@router.message(F.text == BTN_DECK)
async def show_deck(message: Message, session: AsyncSession) -> None:
    text, markup = await _render_deck(session, message.from_user.id)
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data == CB_DECK_OPEN)
async def cb_open_deck(callback: CallbackQuery, session: AsyncSession) -> None:
    text, markup = await _render_deck(session, callback.from_user.id)
    await callback.answer()
    # Экран крутки/шансов — это фото с подписью, редактировать его в текстовое
    # сообщение нельзя (разные типы контента у Telegram) — поэтому всегда новое сообщение.
    await callback.message.answer(text, reply_markup=markup)


async def _get_ready_user(callback: CallbackQuery, session: AsyncSession):
    """Общая проверка для roll1/roll10: игрок зарегистрирован и выбрал вселенную.
    Возвращает User либо None, если уже ответили пользователю и на этом выходим."""
    user = await get_by_id(session, callback.from_user.id)
    if user is None:
        await callback.answer()
        await callback.message.answer(NEED_START)
        return None
    if user.universe_selected is None:
        await callback.answer(NO_UNIVERSE_SELECTED, show_alert=True)
        return None
    return user


@router.callback_query(F.data == CB_DECK_ROLL1)
async def cb_roll1(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    user_id = callback.from_user.id
    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_ROLL), ttl_ms=8000) as acquired:
        if not acquired:
            await callback.answer()
            return

        user = await _get_ready_user(callback, session)
        if user is None:
            return
        await callback.answer()

        try:
            result = await roll_one(session, redis, user_id=user_id, universe_code=user.universe_selected)
        except NoActiveSeasonError:
            await callback.message.answer(NO_ACTIVE_SEASON)
            return
        except UniverseNotReadyError as exc:
            await callback.message.answer(
                UNIVERSE_NOT_READY.format(
                    universe=esc(user.universe_selected), tiers=", ".join(map(str, exc.missing_tiers))
                )
            )
            return
        except NotEnoughTicketsError as exc:
            await callback.message.answer(NOT_ENOUGH_TICKETS.format(needed=exc.needed, cap=TICKET_NATURAL_CAP))
            return

        universe = await get_universe(session, user.universe_selected)
        caption = _card_caption(result.card, result.stars, universe.title, result.owned_quantity)
        await callback.message.answer_photo(card_photo(result.card), caption=caption, reply_markup=back_to_deck())


@router.callback_query(F.data == CB_DECK_ROLL10)
async def cb_roll10(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    user_id = callback.from_user.id
    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_ROLL), ttl_ms=8000) as acquired:
        if not acquired:
            await callback.answer()
            return

        user = await _get_ready_user(callback, session)
        if user is None:
            return
        await callback.answer()

        try:
            results: list[RollResult] = await roll_ten(
                session, redis, user_id=user_id, universe_code=user.universe_selected
            )
        except NoActiveSeasonError:
            await callback.message.answer(NO_ACTIVE_SEASON)
            return
        except UniverseNotReadyError as exc:
            await callback.message.answer(
                UNIVERSE_NOT_READY.format(
                    universe=esc(user.universe_selected), tiers=", ".join(map(str, exc.missing_tiers))
                )
            )
            return
        except NotEnoughTicketsError as exc:
            await callback.message.answer(NOT_ENOUGH_TICKETS.format(needed=exc.needed, cap=TICKET_NATURAL_CAP))
            return

        universe = await get_universe(session, user.universe_selected)
        top = max(results, key=lambda r: r.card.base_ubp)
        caption = _card_caption(top.card, top.stars, universe.title, top.owned_quantity)
        await callback.message.answer_photo(card_photo(top.card), caption=caption)

        # Отдельным сообщением, а не в подписи к фото — подпись у Telegram ограничена
        # 1024 символами, а с описаниями карт список из 10 строк легко её превысит.
        breakdown = ROLL_TEN_RESULT_HEADER + "".join(
            ROLL_TEN_LINE.format(i=i + 1, name=esc(r.card.name), ubp=r.card.base_ubp)
            for i, r in enumerate(results)
        )
        await callback.message.answer(breakdown, reply_markup=back_to_deck())


async def _get_ready_tier_map(callback: CallbackQuery, session: AsyncSession, universe: Universe) -> dict[int, list[Card]] | None:
    try:
        return await get_tier_map(session, universe.code)
    except UniverseNotReadyError as exc:
        await callback.message.answer(
            UNIVERSE_NOT_READY.format(universe=esc(universe.title), tiers=", ".join(map(str, exc.missing_tiers)))
        )
        return None


async def _render_chances_overview(callback: CallbackQuery, session: AsyncSession, universe_code: str) -> tuple[str, object] | None:
    universe = await get_universe(session, universe_code)
    tier_map = await _get_ready_tier_map(callback, session, universe)
    if tier_map is None:
        return None
    return CHANCES_HEADER.format(universe=esc(universe.title)), chances_menu(tier_map)


@router.callback_query(F.data == CB_DECK_CHANCES)
async def cb_chances(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_by_id(session, callback.from_user.id)
    if user is None or user.universe_selected is None:
        await callback.answer(NO_UNIVERSE_SELECTED, show_alert=True)
        return
    await callback.answer()

    rendered = await _render_chances_overview(callback, session, user.universe_selected)
    if rendered is None:
        return
    text, markup = rendered
    # Вход из "Колоды" — новое сообщение (тот же паттерн, что и у результатов крутки),
    # родительский экран "Колода" остаётся видимым выше.
    await callback.message.answer(text, reply_markup=markup)


@router.callback_query(F.data == CB_DECK_CHANCES_BACK)
async def cb_chances_back(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_by_id(session, callback.from_user.id)
    if user is None or user.universe_selected is None:
        await callback.answer(NO_UNIVERSE_SELECTED, show_alert=True)
        return
    await callback.answer()

    rendered = await _render_chances_overview(callback, session, user.universe_selected)
    if rendered is None:
        return
    text, markup = rendered
    # Назад из детального экрана тира — редактируем ТО ЖЕ сообщение, а не плодим новое.
    await safe_edit_text(callback.message, text, reply_markup=markup)


@router.callback_query(F.data.startswith(CB_DECK_CHANCES_TIER_PREFIX))
async def cb_chances_tier(callback: CallbackQuery, session: AsyncSession) -> None:
    tier = int(callback.data[len(CB_DECK_CHANCES_TIER_PREFIX) :])

    user = await get_by_id(session, callback.from_user.id)
    if user is None or user.universe_selected is None:
        await callback.answer(NO_UNIVERSE_SELECTED, show_alert=True)
        return
    await callback.answer()

    universe = await get_universe(session, user.universe_selected)
    tier_map = await _get_ready_tier_map(callback, session, universe)
    if tier_map is None or tier not in tier_map:
        return

    discovered = await get_discovered_card_ids(session, callback.from_user.id, user.universe_selected)

    header = CHANCES_TIER_HEADER.format(
        emoji=TIER_EMOJI[tier], name=TIER_NAMES[tier], chance=TIER_CHANCE_PERCENT[tier], count=len(tier_map[tier])
    )
    lines = "".join(
        CHANCES_CARD_LINE.format(i=i, name=esc(card.name) if card.id in discovered else CHANCES_UNDISCOVERED)
        for i, card in enumerate(sorted(tier_map[tier], key=lambda c: c.external_id), start=1)
    )
    await safe_edit_text(callback.message, header + lines, reply_markup=chances_tier_menu())
