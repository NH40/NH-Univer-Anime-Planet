from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.settings import get_settings
from bot.config.game import TICKET_CAP_SLOT_BONUS
from bot.constant.admin import (
    CB_ADMIN_FIND_PLAYER_START,
    CB_ADMIN_GIVE_CARD_CARD_PREFIX,
    CB_ADMIN_GIVE_CARD_PAGE_PREFIX,
    CB_ADMIN_GIVE_CARD_UNIVERSE_PREFIX,
    CB_ADMIN_OPEN,
    CB_ADMIN_PLAYER_BAN_TOGGLE_PREFIX,
    CB_ADMIN_PLAYER_GIVE_CARD_PREFIX,
    CB_ADMIN_PLAYER_GIVE_COINS_PREFIX,
    CB_ADMIN_PLAYER_GIVE_DUST_PREFIX,
    CB_ADMIN_PLAYER_GIVE_TICKET_CAP_PERMANENT_PREFIX,
    CB_ADMIN_PLAYER_GIVE_TICKET_CAP_SEASONAL_PREFIX,
    CB_ADMIN_PLAYER_VIEW_PREFIX,
    CB_ADMIN_STATS,
    CB_ADMIN_TECH_MODE_TOGGLE,
    TRANSACTION_REASON_ADMIN_GRANT_COINS,
    TRANSACTION_REASON_ADMIN_GRANT_DUST,
)
from bot.db.models.enums import TransactionCurrency
from bot.db.models.transaction import Transaction
from bot.db.models.user import User
from bot.db.repositories import card as card_repo
from bot.db.repositories import clan as clan_repo
from bot.db.repositories import season as season_repo
from bot.db.repositories import universe as universe_repo
from bot.db.repositories.inventory import add_card, decrement_by
from bot.db.repositories.user import (
    add_coins,
    add_dust,
    get_by_id,
    get_by_username,
    grant_ticket_cap_permanent_bonus,
    grant_ticket_cap_seasonal_bonus,
    set_is_banned,
)
from bot.keyboards.admin import (
    admin_menu,
    back_to_admin_menu,
    give_card_card_menu,
    give_card_universe_menu,
    player_card_menu,
)
from bot.services import admin as admin_service
from bot.states.admin import AdminStates
from bot.texts.admin import (
    ACTION_CANCELLED,
    ADMIN_MENU,
    BAN_DONE,
    FIND_PLAYER_NOT_FOUND,
    FIND_PLAYER_PROMPT,
    GIVE_AMOUNT_INVALID,
    GIVE_CARD_DONE,
    GIVE_CARD_INVALID,
    GIVE_CARD_NOT_ENOUGH,
    GIVE_CARD_NOT_FOUND,
    GIVE_CARD_PICK_CARD,
    GIVE_CARD_PICK_UNIVERSE,
    GIVE_CARD_PROMPT,
    GIVE_CARD_REVOKED,
    GIVE_COINS_DONE,
    GIVE_COINS_PROMPT,
    GIVE_DUST_DONE,
    GIVE_DUST_PROMPT,
    GIVE_TICKET_CAP_NO_SEASON,
    GIVE_TICKET_CAP_PERMANENT_DONE,
    GIVE_TICKET_CAP_PERMANENT_PROMPT,
    GIVE_TICKET_CAP_SEASONAL_DONE,
    GIVE_TICKET_CAP_SEASONAL_PROMPT,
    NO_CLAN,
    PLAYER_CARD,
    STATS_SCREEN,
    STATUS_ACTIVE,
    STATUS_BANNED,
    TECH_MODE_DISABLED,
    TECH_MODE_ENABLED,
    UNBAN_DONE,
)
from bot.utils.safe_edit import safe_edit_text

router = Router(name="admin")


async def resolve_player(session: AsyncSession, raw: str) -> User | None:
    raw = raw.strip().lstrip("@")
    if raw.isdigit():
        user = await get_by_id(session, int(raw))
        if user is not None:
            return user
    return await get_by_username(session, raw)


async def _render_player_card(session: AsyncSession, user: User) -> tuple[str, InlineKeyboardMarkup]:
    clan_name = await clan_repo.get_name(session, user.clan_id)
    status = STATUS_BANNED if user.is_banned else STATUS_ACTIVE
    text = PLAYER_CARD.format(
        name=user.display_name or "—",
        id=user.id,
        username=f" @{user.username}" if user.username else "",
        ubp_season=user.ubp_season,
        ubp_total=user.ubp_total,
        dust=user.dust,
        coins=user.coins,
        clan=clan_name or NO_CLAN,
        status=status,
    )
    return text, player_card_menu(user_id=user.id, is_banned=user.is_banned)


# --- Главное меню ---


@router.message(Command("admin"))
async def cmd_admin(message: Message, redis: Redis) -> None:
    tech_mode = await admin_service.get_tech_mode(redis)
    is_super_admin = admin_service.is_config_admin(message.from_user.id, get_settings())
    await message.answer(
        ADMIN_MENU, reply_markup=admin_menu(tech_mode_enabled=tech_mode, is_super_admin=is_super_admin)
    )


@router.callback_query(F.data == CB_ADMIN_OPEN)
async def cb_admin_open(callback: CallbackQuery, redis: Redis) -> None:
    tech_mode = await admin_service.get_tech_mode(redis)
    is_super_admin = admin_service.is_config_admin(callback.from_user.id, get_settings())
    await callback.answer()
    await safe_edit_text(
        callback.message, ADMIN_MENU, reply_markup=admin_menu(tech_mode_enabled=tech_mode, is_super_admin=is_super_admin)
    )


@router.callback_query(F.data == CB_ADMIN_TECH_MODE_TOGGLE)
async def cb_toggle_tech_mode(callback: CallbackQuery, redis: Redis) -> None:
    new_value = not await admin_service.get_tech_mode(redis)
    await admin_service.set_tech_mode(redis, new_value)
    is_super_admin = admin_service.is_config_admin(callback.from_user.id, get_settings())
    await callback.answer(TECH_MODE_ENABLED if new_value else TECH_MODE_DISABLED, show_alert=True)
    await safe_edit_text(
        callback.message, ADMIN_MENU, reply_markup=admin_menu(tech_mode_enabled=new_value, is_super_admin=is_super_admin)
    )


@router.callback_query(F.data == CB_ADMIN_STATS)
async def cb_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    stats = await admin_service.get_stats(session)
    text = STATS_SCREEN.format(
        total_users=stats.total_users,
        online_users=stats.online_users,
        payments_count=stats.payments_count,
        payments_rub=stats.payments_rub,
        cpu_percent=stats.server.cpu_percent,
        ram_used_mb=stats.server.ram_used_mb,
        ram_total_mb=stats.server.ram_total_mb,
        ram_percent=stats.server.ram_percent,
        disk_used_gb=stats.server.disk_used_gb,
        disk_total_gb=stats.server.disk_total_gb,
        disk_percent=stats.server.disk_percent,
    )
    await safe_edit_text(callback.message, text, reply_markup=back_to_admin_menu())


# --- Найти игрока ---


@router.callback_query(F.data == CB_ADMIN_FIND_PLAYER_START)
async def cb_find_player_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_find_player)
    await callback.answer()
    await safe_edit_text(callback.message, FIND_PLAYER_PROMPT, reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))


@router.message(StateFilter(AdminStates.waiting_find_player), Command("cancel"))
async def cancel_find_player(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ACTION_CANCELLED)


@router.message(StateFilter(AdminStates.waiting_find_player))
async def apply_find_player(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user = await resolve_player(session, message.text or "")
    if user is None:
        await message.answer(FIND_PLAYER_NOT_FOUND)
        return

    await state.clear()
    text, keyboard = await _render_player_card(session, user)
    await message.answer(text, reply_markup=keyboard)


# --- Выдать пыль ---


@router.callback_query(F.data.startswith(CB_ADMIN_PLAYER_GIVE_DUST_PREFIX))
async def cb_give_dust_start(callback: CallbackQuery, state: FSMContext) -> None:
    target_id = int(callback.data[len(CB_ADMIN_PLAYER_GIVE_DUST_PREFIX) :])
    await state.set_state(AdminStates.waiting_give_dust)
    await state.update_data(target_user_id=target_id)
    await callback.answer()
    await safe_edit_text(callback.message, GIVE_DUST_PROMPT, reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))


@router.message(StateFilter(AdminStates.waiting_give_dust), Command("cancel"))
async def cancel_give_dust(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ACTION_CANCELLED)


@router.message(StateFilter(AdminStates.waiting_give_dust))
async def apply_give_dust(message: Message, state: FSMContext, session: AsyncSession) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer(GIVE_AMOUNT_INVALID)
        return

    amount = int(raw)
    data = await state.get_data()
    target_id = data.get("target_user_id")
    await state.clear()

    target = await get_by_id(session, target_id) if target_id is not None else None
    if target is None:
        await message.answer(FIND_PLAYER_NOT_FOUND)
        return

    await add_dust(session, user_id=target_id, amount=amount)
    session.add(
        Transaction(
            user_id=target_id,
            currency=TransactionCurrency.dust,
            amount=amount,
            reason=TRANSACTION_REASON_ADMIN_GRANT_DUST,
            admin_id=message.from_user.id,
        )
    )
    await session.commit()

    name = target.display_name or str(target.id)
    await message.answer(GIVE_DUST_DONE.format(amount=amount, name=name))

    target = await get_by_id(session, target_id)
    text, keyboard = await _render_player_card(session, target)
    await message.answer(text, reply_markup=keyboard)


# --- Выдать коины ---


@router.callback_query(F.data.startswith(CB_ADMIN_PLAYER_GIVE_COINS_PREFIX))
async def cb_give_coins_start(callback: CallbackQuery, state: FSMContext) -> None:
    target_id = int(callback.data[len(CB_ADMIN_PLAYER_GIVE_COINS_PREFIX) :])
    await state.set_state(AdminStates.waiting_give_coins)
    await state.update_data(target_user_id=target_id)
    await callback.answer()
    await safe_edit_text(callback.message, GIVE_COINS_PROMPT, reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))


@router.message(StateFilter(AdminStates.waiting_give_coins), Command("cancel"))
async def cancel_give_coins(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ACTION_CANCELLED)


@router.message(StateFilter(AdminStates.waiting_give_coins))
async def apply_give_coins(message: Message, state: FSMContext, session: AsyncSession) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer(GIVE_AMOUNT_INVALID)
        return

    amount = int(raw)
    data = await state.get_data()
    target_id = data.get("target_user_id")
    await state.clear()

    target = await get_by_id(session, target_id) if target_id is not None else None
    if target is None:
        await message.answer(FIND_PLAYER_NOT_FOUND)
        return

    await add_coins(session, user_id=target_id, amount=amount)
    session.add(
        Transaction(
            user_id=target_id,
            currency=TransactionCurrency.coins,
            amount=amount,
            reason=TRANSACTION_REASON_ADMIN_GRANT_COINS,
            admin_id=message.from_user.id,
        )
    )
    await session.commit()

    name = target.display_name or str(target.id)
    await message.answer(GIVE_COINS_DONE.format(amount=amount, name=name))

    target = await get_by_id(session, target_id)
    text, keyboard = await _render_player_card(session, target)
    await message.answer(text, reply_markup=keyboard)


# --- Выдать слот капа тикетов (см. CLAUDE.md, "Магазин: слот капа тикетов") — тот же
# паттерн текстового ввода числа, что выдача пыли/коинов выше. Без Transaction — у
# TransactionCurrency нет варианта "слот капа", тот же принцип, что и у выдачи карточки
# ниже (не пишет Transaction). ---


@router.callback_query(F.data.startswith(CB_ADMIN_PLAYER_GIVE_TICKET_CAP_SEASONAL_PREFIX))
async def cb_give_ticket_cap_seasonal_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    # Сезонный слот без активного сезона выдавать не на что (некуда писать
    # ticket_cap_seasonal_season_id) — гейтим сразу, до запроса количества.
    season = await season_repo.get_active(session)
    if season is None:
        await callback.answer(GIVE_TICKET_CAP_NO_SEASON, show_alert=True)
        return

    target_id = int(callback.data[len(CB_ADMIN_PLAYER_GIVE_TICKET_CAP_SEASONAL_PREFIX) :])
    await state.set_state(AdminStates.waiting_give_ticket_cap_seasonal)
    await state.update_data(target_user_id=target_id)
    await callback.answer()
    await safe_edit_text(
        callback.message, GIVE_TICKET_CAP_SEASONAL_PROMPT, reply_markup=InlineKeyboardMarkup(inline_keyboard=[])
    )


@router.message(StateFilter(AdminStates.waiting_give_ticket_cap_seasonal), Command("cancel"))
async def cancel_give_ticket_cap_seasonal(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ACTION_CANCELLED)


@router.message(StateFilter(AdminStates.waiting_give_ticket_cap_seasonal))
async def apply_give_ticket_cap_seasonal(message: Message, state: FSMContext, session: AsyncSession) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer(GIVE_AMOUNT_INVALID)
        return

    amount = int(raw)
    data = await state.get_data()
    target_id = data.get("target_user_id")
    await state.clear()

    target = await get_by_id(session, target_id) if target_id is not None else None
    season = await season_repo.get_active(session)
    if target is None:
        await message.answer(FIND_PLAYER_NOT_FOUND)
        return
    if season is None:
        await message.answer(GIVE_TICKET_CAP_NO_SEASON)
        return

    new_bonus = await grant_ticket_cap_seasonal_bonus(
        session, user_id=target_id, season_id=season.id, amount=amount * TICKET_CAP_SLOT_BONUS
    )
    await session.commit()

    name = target.display_name or str(target.id)
    await message.answer(GIVE_TICKET_CAP_SEASONAL_DONE.format(amount=amount, name=name, bonus=new_bonus))

    target = await get_by_id(session, target_id)
    text, keyboard = await _render_player_card(session, target)
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith(CB_ADMIN_PLAYER_GIVE_TICKET_CAP_PERMANENT_PREFIX))
async def cb_give_ticket_cap_permanent_start(callback: CallbackQuery, state: FSMContext) -> None:
    target_id = int(callback.data[len(CB_ADMIN_PLAYER_GIVE_TICKET_CAP_PERMANENT_PREFIX) :])
    await state.set_state(AdminStates.waiting_give_ticket_cap_permanent)
    await state.update_data(target_user_id=target_id)
    await callback.answer()
    await safe_edit_text(
        callback.message, GIVE_TICKET_CAP_PERMANENT_PROMPT, reply_markup=InlineKeyboardMarkup(inline_keyboard=[])
    )


@router.message(StateFilter(AdminStates.waiting_give_ticket_cap_permanent), Command("cancel"))
async def cancel_give_ticket_cap_permanent(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ACTION_CANCELLED)


@router.message(StateFilter(AdminStates.waiting_give_ticket_cap_permanent))
async def apply_give_ticket_cap_permanent(message: Message, state: FSMContext, session: AsyncSession) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer(GIVE_AMOUNT_INVALID)
        return

    amount = int(raw)
    data = await state.get_data()
    target_id = data.get("target_user_id")
    await state.clear()

    target = await get_by_id(session, target_id) if target_id is not None else None
    if target is None:
        await message.answer(FIND_PLAYER_NOT_FOUND)
        return

    new_bonus = await grant_ticket_cap_permanent_bonus(session, user_id=target_id, amount=amount * TICKET_CAP_SLOT_BONUS)
    await session.commit()

    name = target.display_name or str(target.id)
    await message.answer(GIVE_TICKET_CAP_PERMANENT_DONE.format(amount=amount, name=name, bonus=new_bonus))

    target = await get_by_id(session, target_id)
    text, keyboard = await _render_player_card(session, target)
    await message.answer(text, reply_markup=keyboard)


# --- Выдать карточку (вселенная -> карта кнопками, звёзды/количество текстом, см.
# CLAUDE.md "Управление карточками: выбор кнопками" — раньше всё вводилось одной строкой
# сырых чисел, включая id карты, который админ физически не мог помнить наизусть) ---

_GIVE_CARD_PAGE_SIZE = 10
_SIGNED_INT_RE = re.compile(r"-?\d+")


@router.callback_query(F.data.startswith(CB_ADMIN_PLAYER_VIEW_PREFIX))
async def cb_player_view(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Возврат к карточке игрока с любого шага выдачи карточки ("Назад")."""
    target_id = int(callback.data[len(CB_ADMIN_PLAYER_VIEW_PREFIX) :])
    await state.clear()
    await callback.answer()
    target = await get_by_id(session, target_id)
    if target is None:
        await safe_edit_text(callback.message, FIND_PLAYER_NOT_FOUND, reply_markup=back_to_admin_menu())
        return
    text, keyboard = await _render_player_card(session, target)
    await safe_edit_text(callback.message, text, reply_markup=keyboard)


@router.callback_query(F.data.startswith(CB_ADMIN_PLAYER_GIVE_CARD_PREFIX))
async def cb_give_card_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    target_id = int(callback.data[len(CB_ADMIN_PLAYER_GIVE_CARD_PREFIX) :])
    await state.update_data(target_user_id=target_id)
    await callback.answer()
    universes = await universe_repo.list_all(session)
    await safe_edit_text(
        callback.message, GIVE_CARD_PICK_UNIVERSE, reply_markup=give_card_universe_menu(universes, user_id=target_id)
    )


async def _show_card_page(callback: CallbackQuery, state: FSMContext, session: AsyncSession, *, page: int) -> None:
    data = await state.get_data()
    target_id = data.get("target_user_id")
    universe_code = data.get("give_card_universe")
    if target_id is None or universe_code is None:
        # Экран устарел (например, состояние потерялось) — откатываемся к карточке игрока,
        # если известен id, иначе в главное admin-меню.
        if target_id is not None:
            target = await get_by_id(session, target_id)
            if target is not None:
                text, keyboard = await _render_player_card(session, target)
                await safe_edit_text(callback.message, text, reply_markup=keyboard)
                return
        await safe_edit_text(callback.message, ADMIN_MENU, reply_markup=back_to_admin_menu())
        return

    universe = await universe_repo.get_by_code(session, universe_code)
    all_cards = await card_repo.list_by_universe(session, universe_code)
    total_pages = max(1, -(-len(all_cards) // _GIVE_CARD_PAGE_SIZE))
    page = max(1, min(page, total_pages))
    await state.update_data(give_card_page=page)
    start = (page - 1) * _GIVE_CARD_PAGE_SIZE
    page_cards = all_cards[start : start + _GIVE_CARD_PAGE_SIZE]

    text = GIVE_CARD_PICK_CARD.format(
        universe=universe.title if universe is not None else universe_code, page=page, total_pages=total_pages
    )
    await safe_edit_text(
        callback.message, text, reply_markup=give_card_card_menu(page_cards, page=page, total_pages=total_pages, user_id=target_id)
    )


@router.callback_query(F.data.startswith(CB_ADMIN_GIVE_CARD_UNIVERSE_PREFIX))
async def cb_give_card_pick_universe(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    universe_code = callback.data[len(CB_ADMIN_GIVE_CARD_UNIVERSE_PREFIX) :]
    await state.update_data(give_card_universe=universe_code)
    await callback.answer()
    await _show_card_page(callback, state, session, page=1)


@router.callback_query(F.data.startswith(CB_ADMIN_GIVE_CARD_PAGE_PREFIX))
async def cb_give_card_page(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    page = int(callback.data[len(CB_ADMIN_GIVE_CARD_PAGE_PREFIX) :])
    await callback.answer()
    await _show_card_page(callback, state, session, page=page)


@router.callback_query(F.data.startswith(CB_ADMIN_GIVE_CARD_CARD_PREFIX))
async def cb_give_card_pick_card(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    card_id = int(callback.data[len(CB_ADMIN_GIVE_CARD_CARD_PREFIX) :])
    card = await card_repo.get_by_id(session, card_id)
    await callback.answer()
    if card is None:
        await safe_edit_text(callback.message, GIVE_CARD_NOT_FOUND, reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))
        return

    await state.update_data(give_card_id=card_id)
    await state.set_state(AdminStates.waiting_give_card)
    await safe_edit_text(
        callback.message,
        GIVE_CARD_PROMPT.format(card_name=card.name),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[]),
    )


@router.message(StateFilter(AdminStates.waiting_give_card), Command("cancel"))
async def cancel_give_card(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ACTION_CANCELLED)


@router.message(StateFilter(AdminStates.waiting_give_card))
async def apply_give_card(message: Message, state: FSMContext, session: AsyncSession) -> None:
    parts = (message.text or "").strip().split()
    if len(parts) != 2 or not parts[0].isdigit() or not _SIGNED_INT_RE.fullmatch(parts[1]):
        await message.answer(GIVE_CARD_INVALID)
        return

    stars, qty = int(parts[0]), int(parts[1])
    if stars <= 0 or qty == 0:
        await message.answer(GIVE_CARD_INVALID)
        return

    data = await state.get_data()
    target_id = data.get("target_user_id")
    card_id = data.get("give_card_id")
    if target_id is None or card_id is None:
        await state.clear()
        await message.answer(GIVE_CARD_NOT_FOUND)
        return

    card = await card_repo.get_by_id(session, card_id)
    if card is None:
        await state.clear()
        await message.answer(GIVE_CARD_NOT_FOUND)
        return

    target = await get_by_id(session, target_id)
    if target is None:
        await state.clear()
        await message.answer(FIND_PLAYER_NOT_FOUND)
        return

    await state.clear()
    name = target.display_name or str(target.id)

    if qty > 0:
        await add_card(session, user_id=target_id, card_id=card_id, stars=stars, qty=qty)
        await session.commit()
        await message.answer(GIVE_CARD_DONE.format(card_name=card.name, stars=stars, qty=qty, name=name))
    else:
        ok = await decrement_by(session, user_id=target_id, card_id=card_id, stars=stars, amount=-qty)
        if not ok:
            await message.answer(GIVE_CARD_NOT_ENOUGH)
            return
        await session.commit()
        await message.answer(GIVE_CARD_REVOKED.format(card_name=card.name, stars=stars, qty=-qty, name=name))

    text, keyboard = await _render_player_card(session, target)
    await message.answer(text, reply_markup=keyboard)

    text, keyboard = await _render_player_card(session, target)
    await message.answer(text, reply_markup=keyboard)


# --- Бан/анбан ---


@router.callback_query(F.data.startswith(CB_ADMIN_PLAYER_BAN_TOGGLE_PREFIX))
async def cb_toggle_ban(callback: CallbackQuery, session: AsyncSession) -> None:
    target_id = int(callback.data[len(CB_ADMIN_PLAYER_BAN_TOGGLE_PREFIX) :])
    target = await get_by_id(session, target_id)
    if target is None:
        await callback.answer(FIND_PLAYER_NOT_FOUND, show_alert=True)
        return

    new_value = not target.is_banned
    await set_is_banned(session, user_id=target_id, enabled=new_value)
    name = target.display_name or str(target.id)
    await callback.answer(BAN_DONE.format(name=name) if new_value else UNBAN_DONE.format(name=name), show_alert=True)

    target = await get_by_id(session, target_id)
    text, keyboard = await _render_player_card(session, target)
    await safe_edit_text(callback.message, text, reply_markup=keyboard)
