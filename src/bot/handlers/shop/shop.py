from __future__ import annotations

from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.keys import action_lock
from bot.cache.lock import try_acquire
from bot.config.game import (
    BATTLE_PASS_PRICE_COINS,
    SHOP_COIN_TICKET_MAX_QUANTITY,
    SHOP_COIN_TICKET_PRICE,
    SHOP_TICKET_MAX_QUANTITY,
    SHOP_TICKET_PRICE_DUST,
    SUBSCRIPTION_DURATION_DAYS,
    SUBSCRIPTION_PRICE_COINS,
    TICKET_CAP_SLOT_BONUS,
    TICKET_CAP_SLOT_MAX_QUANTITY,
    TICKET_CAP_SLOT_PRICE_PERMANENT_COINS,
    TICKET_CAP_SLOT_PRICE_SEASONAL_COINS,
    TICKET_NATURAL_CAP,
)
from bot.constant.shop import (
    CB_COINSHOP_BATTLE_PASS,
    CB_COINSHOP_BATTLE_PASS_CONFIRM,
    CB_COINSHOP_CANCEL,
    CB_COINSHOP_SUBSCRIPTION,
    CB_COINSHOP_SUBSCRIPTION_CONFIRM,
    CB_COINSHOP_TICKET_CAP,
    CB_COINSHOP_TICKET_CAP_ASK_PREFIX,
    CB_COINSHOP_TICKET_CAP_BUY_PREFIX,
    CB_COINSHOP_TICKET_CAP_CUSTOM_PREFIX,
    CB_COINSHOP_TICKET_CAP_PERMANENT,
    CB_COINSHOP_TICKET_CAP_SEASONAL,
    CB_COINSHOP_TICKETS,
    CB_COINSHOP_TICKETS_CONFIRM,
    CB_SHOP_BUY_TICKETS_CUSTOM,
    CB_SHOP_BUY_TICKETS_MAX,
    CB_SHOP_BUY_TICKETS_PREFIX,
    CB_SHOP_COINS,
    CB_SHOP_DUST,
    CB_SHOP_OPEN,
    LOCK_ACTION_BUY_BATTLE_PASS,
    LOCK_ACTION_BUY_SUBSCRIPTION,
    LOCK_ACTION_BUY_TICKET_CAP,
    LOCK_ACTION_BUY_TICKETS,
    TICKET_CAP_KIND_PERMANENT,
    TICKET_CAP_KIND_SEASONAL,
)
from bot.db.models.user import User
from bot.db.repositories.user import get_by_id
from bot.keyboards.shop import (
    battle_pass_menu,
    coin_shop_menu,
    coin_tickets_confirm_menu,
    dust_shop_menu,
    shop_menu,
    subscription_menu,
    ticket_cap_ask_menu,
    ticket_cap_menu,
    ticket_cap_quantity_menu,
)
from bot.services import battle_pass as pass_service
from bot.services import shop
from bot.states.shop import ShopStates
from bot.texts.common import BTN_SHOP, NEED_START
from bot.texts.shop import (
    BATTLE_PASS_ALREADY_PREMIUM,
    BATTLE_PASS_BOUGHT,
    BATTLE_PASS_NO_SEASON,
    BATTLE_PASS_SCREEN,
    BATTLE_PASS_STATUS_ACTIVE,
    BATTLE_PASS_STATUS_NONE,
    BUY_MAX_NOTHING,
    BUY_TICKETS_RESULT,
    BUY_TICKETS_RESULT_ALERT,
    CANCELLED,
    COIN_SHOP_SCREEN,
    COIN_TICKETS_BOUGHT,
    COIN_TICKETS_CONFIRM,
    COIN_TICKETS_INVALID,
    COIN_TICKETS_SCREEN,
    CUSTOM_QUANTITY_CANCELLED,
    CUSTOM_QUANTITY_INVALID,
    CUSTOM_QUANTITY_PROMPT,
    DUST_SHOP_SCREEN,
    NOT_ENOUGH_COINS,
    NOT_ENOUGH_DUST,
    SHOP_SCREEN,
    SUBSCRIPTION_BOUGHT,
    SUBSCRIPTION_SCREEN,
    SUBSCRIPTION_STATUS_ACTIVE,
    SUBSCRIPTION_STATUS_NONE,
    TICKET_CAP_ASK_PERMANENT,
    TICKET_CAP_ASK_SEASONAL,
    TICKET_CAP_BOUGHT,
    TICKET_CAP_CUSTOM_INVALID,
    TICKET_CAP_CUSTOM_PROMPT,
    TICKET_CAP_NO_SEASON,
    TICKET_CAP_QUANTITY_SCREEN_PERMANENT,
    TICKET_CAP_QUANTITY_SCREEN_SEASONAL,
    TICKET_CAP_SCREEN,
)
from bot.utils.safe_edit import safe_edit_text

router = Router(name="shop")

_DATE_FMT = "%d.%m.%Y %H:%M"


def _fmt(until: datetime | None) -> str | None:
    """Форматирует дату истечения, если она ещё в будущем — иначе None (значит "не активно")."""
    if until is None or until <= datetime.now(timezone.utc):
        return None
    return until.strftime(_DATE_FMT)


def _shop_text(user: User) -> str:
    return SHOP_SCREEN.format(dust=user.dust, coins=user.coins)


def _dust_shop_text(user: User) -> str:
    return DUST_SHOP_SCREEN.format(dust=user.dust, price=SHOP_TICKET_PRICE_DUST)


def _coin_shop_text(user: User) -> str:
    return COIN_SHOP_SCREEN.format(coins=user.coins)


def _subscription_text(user: User) -> str:
    active_until = _fmt(user.subscription_until)
    status = SUBSCRIPTION_STATUS_ACTIVE.format(until=active_until) if active_until else SUBSCRIPTION_STATUS_NONE
    return SUBSCRIPTION_SCREEN.format(
        price=SUBSCRIPTION_PRICE_COINS, days=SUBSCRIPTION_DURATION_DAYS, status=status, coins=user.coins
    )


async def _battle_pass_text(session: AsyncSession, user: User) -> tuple[str, bool]:
    """Возвращает (текст, is_premium) — статус читается из BattlePass.is_premium текущего
    сезона (services/battle_pass), а не из User.premium_pass_until: премиум-ветка
    открывается разово на весь сезон, не по дням (см. CLAUDE.md, "Сезонный пасс")."""
    is_premium = await pass_service.is_premium(session, user_id=user.id)
    status = BATTLE_PASS_STATUS_ACTIVE if is_premium else BATTLE_PASS_STATUS_NONE
    text = BATTLE_PASS_SCREEN.format(price=BATTLE_PASS_PRICE_COINS, status=status, coins=user.coins)
    return text, is_premium


def _coin_tickets_text(user: User) -> str:
    return COIN_TICKETS_SCREEN.format(
        price=SHOP_COIN_TICKET_PRICE, coins=user.coins, max=SHOP_COIN_TICKET_MAX_QUANTITY
    )


@router.message(Command("shop"))
@router.message(F.text == BTN_SHOP)
async def show_shop(message: Message, session: AsyncSession) -> None:
    user = await get_by_id(session, message.from_user.id)
    if user is None:
        await message.answer(NEED_START)
        return
    await message.answer(_shop_text(user), reply_markup=shop_menu())


@router.callback_query(F.data == CB_SHOP_OPEN)
async def cb_open_shop(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_by_id(session, callback.from_user.id)
    await callback.answer()
    if user is None:
        await callback.message.answer(NEED_START)
        return
    await safe_edit_text(callback.message, _shop_text(user), reply_markup=shop_menu())


@router.callback_query(F.data == CB_SHOP_DUST)
async def cb_open_dust_shop(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_by_id(session, callback.from_user.id)
    await callback.answer()
    if user is None:
        await callback.message.answer(NEED_START)
        return
    await safe_edit_text(callback.message, _dust_shop_text(user), reply_markup=dust_shop_menu())


@router.callback_query(F.data == CB_SHOP_COINS)
async def cb_open_coin_shop(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_by_id(session, callback.from_user.id)
    await callback.answer()
    if user is None:
        await callback.message.answer(NEED_START)
        return
    await safe_edit_text(callback.message, _coin_shop_text(user), reply_markup=coin_shop_menu())


async def _buy_tickets_and_refresh(
    callback: CallbackQuery, session: AsyncSession, redis: Redis, quantity: int
) -> None:
    user_id = callback.from_user.id
    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_BUY_TICKETS)) as acquired:
        if not acquired:
            await callback.answer()
            return

        try:
            cost = await shop.buy_tickets(session, user_id=user_id, quantity=quantity)
        except shop.NotEnoughDustError as exc:
            await callback.answer(NOT_ENOUGH_DUST.format(needed=exc.needed), show_alert=True)
            return

        await callback.answer(BUY_TICKETS_RESULT_ALERT.format(qty=quantity, cost=cost), show_alert=True)

        user = await get_by_id(session, user_id)
        if user is not None:
            await safe_edit_text(callback.message, _dust_shop_text(user), reply_markup=dust_shop_menu())


@router.callback_query(F.data.startswith(CB_SHOP_BUY_TICKETS_PREFIX))
async def cb_buy_tickets_preset(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    quantity = int(callback.data[len(CB_SHOP_BUY_TICKETS_PREFIX) :])
    await _buy_tickets_and_refresh(callback, session, redis, quantity)


@router.callback_query(F.data == CB_SHOP_BUY_TICKETS_MAX)
async def cb_buy_tickets_max(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    user = await get_by_id(session, callback.from_user.id)
    if user is None:
        await callback.answer(NEED_START, show_alert=True)
        return

    quantity = min(user.dust // SHOP_TICKET_PRICE_DUST, SHOP_TICKET_MAX_QUANTITY)
    if quantity < 1:
        await callback.answer(BUY_MAX_NOTHING, show_alert=True)
        return
    await _buy_tickets_and_refresh(callback, session, redis, quantity)


@router.callback_query(F.data == CB_SHOP_BUY_TICKETS_CUSTOM)
async def cb_buy_tickets_custom_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ShopStates.waiting_ticket_quantity)
    await callback.answer()
    await callback.message.answer(CUSTOM_QUANTITY_PROMPT.format(max=SHOP_TICKET_MAX_QUANTITY))


@router.message(StateFilter(ShopStates.waiting_ticket_quantity), Command("cancel"))
async def cancel_custom_quantity(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(CUSTOM_QUANTITY_CANCELLED)


@router.message(StateFilter(ShopStates.waiting_ticket_quantity))
async def apply_custom_quantity(message: Message, state: FSMContext, session: AsyncSession) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or not (1 <= int(raw) <= SHOP_TICKET_MAX_QUANTITY):
        await message.answer(CUSTOM_QUANTITY_INVALID.format(max=SHOP_TICKET_MAX_QUANTITY))
        return

    quantity = int(raw)
    await state.clear()

    try:
        cost = await shop.buy_tickets(session, user_id=message.from_user.id, quantity=quantity)
    except shop.NotEnoughDustError as exc:
        await message.answer(NOT_ENOUGH_DUST.format(needed=exc.needed))
        return

    await message.answer(BUY_TICKETS_RESULT.format(qty=quantity, cost=cost))


# --- Подписка ---


@router.callback_query(F.data == CB_COINSHOP_SUBSCRIPTION)
async def cb_open_subscription(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_by_id(session, callback.from_user.id)
    await callback.answer()
    if user is None:
        await callback.message.answer(NEED_START)
        return
    await safe_edit_text(
        callback.message, _subscription_text(user), reply_markup=subscription_menu(SUBSCRIPTION_PRICE_COINS)
    )


@router.callback_query(F.data == CB_COINSHOP_SUBSCRIPTION_CONFIRM)
async def cb_buy_subscription(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    user_id = callback.from_user.id
    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_BUY_SUBSCRIPTION)) as acquired:
        if not acquired:
            await callback.answer()
            return

        try:
            new_until = await shop.buy_subscription(session, user_id=user_id)
        except shop.NotEnoughCoinsError as exc:
            await callback.answer(NOT_ENOUGH_COINS.format(needed=exc.needed), show_alert=True)
            return

        await callback.answer(SUBSCRIPTION_BOUGHT.format(until=new_until.strftime(_DATE_FMT)), show_alert=True)

        user = await get_by_id(session, user_id)
        if user is not None:
            await safe_edit_text(
                callback.message, _subscription_text(user), reply_markup=subscription_menu(SUBSCRIPTION_PRICE_COINS)
            )


# --- Battle Pass (только покупка премиум-доступа, см. services/shop) ---


@router.callback_query(F.data == CB_COINSHOP_BATTLE_PASS)
async def cb_open_battle_pass(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_by_id(session, callback.from_user.id)
    await callback.answer()
    if user is None:
        await callback.message.answer(NEED_START)
        return
    text, is_premium = await _battle_pass_text(session, user)
    await safe_edit_text(
        callback.message, text, reply_markup=battle_pass_menu(BATTLE_PASS_PRICE_COINS, already_premium=is_premium)
    )


@router.callback_query(F.data == CB_COINSHOP_BATTLE_PASS_CONFIRM)
async def cb_buy_battle_pass(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    user_id = callback.from_user.id
    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_BUY_BATTLE_PASS)) as acquired:
        if not acquired:
            await callback.answer()
            return

        try:
            await shop.buy_premium_pass(session, user_id=user_id)
        except shop.NoActiveSeasonError:
            await callback.answer(BATTLE_PASS_NO_SEASON, show_alert=True)
            return
        except shop.AlreadyPremiumError:
            await callback.answer(BATTLE_PASS_ALREADY_PREMIUM, show_alert=True)
            return
        except shop.NotEnoughCoinsError as exc:
            await callback.answer(NOT_ENOUGH_COINS.format(needed=exc.needed), show_alert=True)
            return

        await callback.answer(BATTLE_PASS_BOUGHT, show_alert=True)

        user = await get_by_id(session, user_id)
        if user is not None:
            text, is_premium = await _battle_pass_text(session, user)
            await safe_edit_text(
                callback.message, text, reply_markup=battle_pass_menu(BATTLE_PASS_PRICE_COINS, already_premium=is_premium)
            )


# --- Тикеты за коины (ввод количества -> подтверждение -> покупка) ---


@router.callback_query(F.data == CB_COINSHOP_TICKETS)
async def cb_open_coin_tickets(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    user = await get_by_id(session, callback.from_user.id)
    await callback.answer()
    if user is None:
        await callback.message.answer(NEED_START)
        return
    await state.set_state(ShopStates.waiting_coin_ticket_quantity)
    # edit_text без reply_markup СОХРАНЯЕТ старую клавиатуру (кнопки категорий магазина
    # коинов), а не убирает — явно очищаем, иначе можно нажать "Battle Pass" прямо во
    # время ожидания ввода числа и запутать FSM-состояние (см. CLAUDE.md).
    await safe_edit_text(callback.message, _coin_tickets_text(user), reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))


@router.message(StateFilter(ShopStates.waiting_coin_ticket_quantity), Command("cancel"))
async def cancel_coin_tickets(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(CANCELLED)


@router.message(StateFilter(ShopStates.waiting_coin_ticket_quantity))
async def apply_coin_ticket_quantity(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or not (1 <= int(raw) <= SHOP_COIN_TICKET_MAX_QUANTITY):
        await message.answer(COIN_TICKETS_INVALID.format(max=SHOP_COIN_TICKET_MAX_QUANTITY))
        return

    quantity = int(raw)
    cost = quantity * SHOP_COIN_TICKET_PRICE
    await state.update_data(quantity=quantity)
    await message.answer(
        COIN_TICKETS_CONFIRM.format(qty=quantity, cost=cost), reply_markup=coin_tickets_confirm_menu()
    )


@router.callback_query(StateFilter(ShopStates.waiting_coin_ticket_quantity), F.data == CB_COINSHOP_TICKETS_CONFIRM)
async def cb_confirm_coin_tickets(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    quantity = data.get("quantity")
    await state.clear()

    if quantity is None:
        await callback.answer(CANCELLED, show_alert=True)
        return

    try:
        cost = await shop.buy_tickets_with_coins(session, user_id=callback.from_user.id, quantity=quantity)
    except shop.NotEnoughCoinsError as exc:
        await callback.answer(NOT_ENOUGH_COINS.format(needed=exc.needed), show_alert=True)
        return

    await callback.answer()
    await callback.message.answer(COIN_TICKETS_BOUGHT.format(qty=quantity, cost=cost))


@router.callback_query(F.data == CB_COINSHOP_CANCEL)
async def cb_cancel_pending_purchase(callback: CallbackQuery, state: FSMContext) -> None:
    """Общая отмена для флоу "ввели число -> подтвердите" — тикеты за коины и масс-крутка
    казино (см. handlers/casino) шарят один и тот же callback."""
    await state.clear()
    await callback.answer()
    await callback.message.answer(CANCELLED)


# --- Слот капа тикетов (за коины — пакет в магазине коинов, см. CLAUDE.md, "Магазин: слот
# капа тикетов"; изменено 2026-08-17, раньше был за рубли через YooKassa-инвойс) ---

_TICKET_CAP_PRICE_BY_KIND = {
    TICKET_CAP_KIND_SEASONAL: TICKET_CAP_SLOT_PRICE_SEASONAL_COINS,
    TICKET_CAP_KIND_PERMANENT: TICKET_CAP_SLOT_PRICE_PERMANENT_COINS,
}
_TICKET_CAP_QUANTITY_SCREEN_BY_KIND = {
    TICKET_CAP_KIND_SEASONAL: TICKET_CAP_QUANTITY_SCREEN_SEASONAL,
    TICKET_CAP_KIND_PERMANENT: TICKET_CAP_QUANTITY_SCREEN_PERMANENT,
}
_TICKET_CAP_ASK_TEXT_BY_KIND = {
    TICKET_CAP_KIND_SEASONAL: TICKET_CAP_ASK_SEASONAL,
    TICKET_CAP_KIND_PERMANENT: TICKET_CAP_ASK_PERMANENT,
}


def _ticket_cap_text(user: User) -> str:
    total_cap = TICKET_NATURAL_CAP + user.ticket_cap_permanent_bonus + user.ticket_cap_seasonal_bonus
    return TICKET_CAP_SCREEN.format(
        bonus=TICKET_CAP_SLOT_BONUS,
        natural_cap=TICKET_NATURAL_CAP,
        permanent=user.ticket_cap_permanent_bonus,
        seasonal=user.ticket_cap_seasonal_bonus,
        total_cap=total_cap,
    )


@router.callback_query(F.data == CB_COINSHOP_TICKET_CAP)
async def cb_open_ticket_cap(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_by_id(session, callback.from_user.id)
    await callback.answer()
    if user is None:
        await callback.message.answer(NEED_START)
        return
    await safe_edit_text(callback.message, _ticket_cap_text(user), reply_markup=ticket_cap_menu())


async def _open_ticket_cap_quantity(callback: CallbackQuery, session: AsyncSession, *, kind: str) -> None:
    user = await get_by_id(session, callback.from_user.id)
    await callback.answer()
    if user is None:
        await callback.message.answer(NEED_START)
        return
    text = _TICKET_CAP_QUANTITY_SCREEN_BY_KIND[kind].format(price=_TICKET_CAP_PRICE_BY_KIND[kind], coins=user.coins)
    await safe_edit_text(callback.message, text, reply_markup=ticket_cap_quantity_menu(kind))


@router.callback_query(F.data == CB_COINSHOP_TICKET_CAP_SEASONAL)
async def cb_open_ticket_cap_seasonal(callback: CallbackQuery, session: AsyncSession) -> None:
    await _open_ticket_cap_quantity(callback, session, kind=TICKET_CAP_KIND_SEASONAL)


@router.callback_query(F.data == CB_COINSHOP_TICKET_CAP_PERMANENT)
async def cb_open_ticket_cap_permanent(callback: CallbackQuery, session: AsyncSession) -> None:
    await _open_ticket_cap_quantity(callback, session, kind=TICKET_CAP_KIND_PERMANENT)


def _ticket_cap_ask_text(*, kind: str, quantity: int) -> str:
    cost = quantity * _TICKET_CAP_PRICE_BY_KIND[kind]
    return _TICKET_CAP_ASK_TEXT_BY_KIND[kind].format(qty=quantity, cost=cost)


@router.callback_query(F.data.startswith(CB_COINSHOP_TICKET_CAP_ASK_PREFIX))
async def cb_ask_ticket_cap_preset(callback: CallbackQuery) -> None:
    """Клик по пресету (1/5/10) — сразу показывает подтверждение, не покупает (тот же
    принцип, что распыление, см. CLAUDE.md)."""
    kind, qty_raw = callback.data[len(CB_COINSHOP_TICKET_CAP_ASK_PREFIX) :].split(":")
    quantity = int(qty_raw)
    await callback.answer()
    await callback.message.answer(
        _ticket_cap_ask_text(kind=kind, quantity=quantity),
        reply_markup=ticket_cap_ask_menu(f"{CB_COINSHOP_TICKET_CAP_BUY_PREFIX}{kind}:{quantity}"),
    )


@router.callback_query(F.data.startswith(CB_COINSHOP_TICKET_CAP_CUSTOM_PREFIX))
async def cb_start_ticket_cap_custom(callback: CallbackQuery, state: FSMContext) -> None:
    kind = callback.data[len(CB_COINSHOP_TICKET_CAP_CUSTOM_PREFIX) :]
    await state.set_state(ShopStates.waiting_ticket_cap_quantity)
    await state.update_data(ticket_cap_kind=kind)
    await callback.answer()
    await callback.message.answer(TICKET_CAP_CUSTOM_PROMPT.format(max=TICKET_CAP_SLOT_MAX_QUANTITY))


@router.message(StateFilter(ShopStates.waiting_ticket_cap_quantity), Command("cancel"))
async def cancel_ticket_cap_custom(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(CUSTOM_QUANTITY_CANCELLED)


@router.message(StateFilter(ShopStates.waiting_ticket_cap_quantity))
async def apply_ticket_cap_custom(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or not (1 <= int(raw) <= TICKET_CAP_SLOT_MAX_QUANTITY):
        await message.answer(TICKET_CAP_CUSTOM_INVALID.format(max=TICKET_CAP_SLOT_MAX_QUANTITY))
        return

    quantity = int(raw)
    data = await state.get_data()
    kind = data.get("ticket_cap_kind")
    await state.clear()
    if kind is None:
        await message.answer(CANCELLED)
        return

    await message.answer(
        _ticket_cap_ask_text(kind=kind, quantity=quantity),
        reply_markup=ticket_cap_ask_menu(f"{CB_COINSHOP_TICKET_CAP_BUY_PREFIX}{kind}:{quantity}"),
    )


@router.callback_query(F.data.startswith(CB_COINSHOP_TICKET_CAP_BUY_PREFIX))
async def cb_buy_ticket_cap(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    kind, qty_raw = callback.data[len(CB_COINSHOP_TICKET_CAP_BUY_PREFIX) :].split(":")
    quantity = int(qty_raw)

    user_id = callback.from_user.id
    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_BUY_TICKET_CAP)) as acquired:
        if not acquired:
            await callback.answer()
            return

        try:
            cost, new_bonus = await shop.buy_ticket_cap_with_coins(session, user_id=user_id, kind=kind, quantity=quantity)
        except shop.NoActiveSeasonError:
            await callback.answer(TICKET_CAP_NO_SEASON, show_alert=True)
            return
        except shop.NotEnoughCoinsError as exc:
            await callback.answer(NOT_ENOUGH_COINS.format(needed=exc.needed), show_alert=True)
            return

        await callback.answer()
        await callback.message.answer(TICKET_CAP_BOUGHT.format(qty=quantity, cost=cost, bonus=new_bonus))
