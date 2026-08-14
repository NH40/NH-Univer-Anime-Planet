from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.keys import action_lock
from bot.cache.lock import try_acquire
from bot.config.game import CLAN_NAME_MAX_LENGTH, CLAN_NAME_MIN_LENGTH
from bot.constant.clan import (
    CB_CLAN_APPLY_PREFIX,
    CB_CLAN_CANCEL_APPLICATION_PREFIX,
    CB_CLAN_CREATE_START,
    CB_CLAN_FIND,
    CB_CLAN_FIND_PAGE_PREFIX,
    CB_CLAN_LEAVE,
    CB_CLAN_LEAVE_CONFIRM,
    CB_CLAN_MEMBERS,
    CB_CLAN_OPEN,
    CB_CLAN_VIEW_PREFIX,
    LOCK_ACTION_APPLY_CLAN,
    LOCK_ACTION_CREATE_CLAN,
)
from bot.db.models.clan import MAX_CLAN_MEMBERS, ClanMember
from bot.db.models.enums import ClanRank
from bot.db.repositories import clan as clan_repo
from bot.db.repositories.user import get_by_id as get_user_by_id
from bot.keyboards.clan import (
    back_to_clan_menu,
    clan_card_menu,
    clan_view_menu,
    find_clans_menu,
    leave_confirm_menu,
    no_clan_menu,
)
from bot.services import clan as clan_service
from bot.states.clan import ClanStates
from bot.texts.clan import (
    ACTION_CANCELLED,
    ALREADY_APPLIED_ELSEWHERE,
    CLAN_CARD,
    CREATE_CLAN_ALREADY_IN_CLAN,
    CREATE_CLAN_DONE,
    CREATE_CLAN_INVALID,
    CREATE_CLAN_PROMPT,
    CREATE_CLAN_TAKEN,
    FIND_CLANS_EMPTY,
    FIND_CLANS_HEADER,
    FIND_CLANS_LINE,
    LEAVE_CONFIRM,
    LEAVE_DONE,
    LEAVE_MUST_TRANSFER,
    MEMBERS_HEADER,
    MEMBERS_LINE,
    NO_CLAN_SCREEN,
    NO_DESCRIPTION,
    NOTIFY_NEW_APPLICATION,
    NOT_IN_CLAN,
    RANK_EMOJI,
    RANK_NAME,
)
from bot.texts.common import BTN_CLAN, NEED_START
from bot.utils.formatting import format_number
from bot.utils.notify import notify
from bot.utils.safe_edit import safe_edit_text

router = Router(name="clan")

CLAN_PAGE_SIZE = 10


def _clan_card_text(view: clan_service.ClanView, owner) -> str:
    return CLAN_CARD.format(
        name=view.clan.name,
        owner_crown=" 👑" if view.is_top10_all_time else "",
        description=(view.clan.description + "\n") if view.clan.description else NO_DESCRIPTION,
        member_count=view.member_count,
        max_members=MAX_CLAN_MEMBERS,
        ubp_season=format_number(view.ubp_season),
        ubp_total=format_number(view.ubp_total),
        owner_name=owner.display_name if owner else "—",
    )


async def _send_card(
    bot: Bot, chat_id: int, old_message: Message | None, text: str, keyboard: InlineKeyboardMarkup, image_path: str | None
) -> None:
    """Карточка клана может быть текстом или фото с подписью (картинка — привилегия
    топ-10 по UBP всего времени, см. services/clan.set_image) — а Telegram не даёт
    конвертировать тип сообщения через edit_text/edit_media. Проще и надёжнее всего
    удалить прежний экран и прислать новый нужного типа, чем гадать, чем был старый."""
    if old_message is not None:
        try:
            await old_message.delete()
        except TelegramAPIError:
            pass
    if image_path:
        await bot.send_photo(chat_id, image_path, caption=text, reply_markup=keyboard)
    else:
        await bot.send_message(chat_id, text, reply_markup=keyboard)


async def render_clan_card(
    bot: Bot, chat_id: int, session: AsyncSession, member: ClanMember, *, old_message: Message | None = None
) -> None:
    """Общий рендер карточки СВОЕГО клана — используется во всех handlers/clan/* файлах,
    когда действие должно вернуть игрока на самый верхний экран клана."""
    view = await clan_service.get_clan_view(session, member.clan_id)
    assert view is not None  # ClanMember.clan_id -> clans FK CASCADE, клан не может исчезнуть под участником

    request_count = 0
    if member.rank in clan_service.MANAGER_RANKS:
        request_count = len(await clan_service.list_applications(session, member.clan_id))

    text = _clan_card_text(view, await get_user_by_id(session, view.clan.owner_id))
    keyboard = clan_card_menu(rank=member.rank, request_count=request_count)
    await _send_card(bot, chat_id, old_message, text, keyboard, view.clan.image_path)


async def render_no_clan_screen(bot: Bot, chat_id: int, old_message: Message | None, session: AsyncSession, user_id: int) -> None:
    invite_count = len(await clan_repo.list_invites_for_user(session, user_id))
    if old_message is not None:
        try:
            await old_message.delete()
        except TelegramAPIError:
            pass
    await bot.send_message(chat_id, NO_CLAN_SCREEN, reply_markup=no_clan_menu(invite_count=invite_count))


async def render_view_page(
    bot: Bot,
    chat_id: int,
    old_message: Message | None,
    session: AsyncSession,
    clan_id: int,
    viewer_id: int,
) -> clan_service.ClanView | None:
    """Карточка ЧУЖОГО клана (просмотр при поиске) — тот же шаблон текста/фото, что и у
    своей карточки, но с кнопками заявки вместо кнопок управления."""
    view = await clan_service.get_clan_view(session, clan_id)
    if view is None:
        return None
    text = _clan_card_text(view, await get_user_by_id(session, view.clan.owner_id))

    viewer_member = await clan_repo.get_member(session, viewer_id)
    can_apply = viewer_member is None
    has_applied = False
    if can_apply:
        request = await clan_repo.get_join_request(session, clan_id=clan_id, user_id=viewer_id)
        has_applied = request is not None and not request.is_invite
    keyboard = clan_view_menu(clan_id=clan_id, has_applied=has_applied, can_apply=can_apply)

    await _send_card(bot, chat_id, old_message, text, keyboard, view.clan.image_path)
    return view


async def _render_find_page(session: AsyncSession, page: int) -> tuple[str, InlineKeyboardMarkup]:
    rows, total_pages = await clan_service.browse_clans(session, by_total=False, page=page, page_size=CLAN_PAGE_SIZE)
    if not rows:
        return FIND_CLANS_EMPTY, find_clans_menu([], page=0, total_pages=1)

    offset = page * CLAN_PAGE_SIZE
    lines = "".join(
        FIND_CLANS_LINE.format(place=offset + i + 1, name=clan.name, ubp=format_number(ubp), members=cnt)
        for i, (clan, ubp, cnt) in enumerate(rows)
    )
    text = FIND_CLANS_HEADER.format(page=page + 1, total_pages=total_pages) + lines
    return text, find_clans_menu(rows, page=page, total_pages=total_pages)


# --- Главный экран ---


@router.message(Command("clan"))
@router.message(F.text == BTN_CLAN)
async def show_clan(message: Message, session: AsyncSession, bot: Bot) -> None:
    user = await get_user_by_id(session, message.from_user.id)
    if user is None:
        await message.answer(NEED_START)
        return

    member = await clan_repo.get_member(session, message.from_user.id)
    if member is None:
        await render_no_clan_screen(bot, message.chat.id, None, session, message.from_user.id)
    else:
        await render_clan_card(bot, message.chat.id, session, member)


@router.callback_query(F.data == CB_CLAN_OPEN)
async def cb_open_clan(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    await callback.answer()
    member = await clan_repo.get_member(session, callback.from_user.id)
    if member is None:
        await render_no_clan_screen(bot, callback.message.chat.id, callback.message, session, callback.from_user.id)
    else:
        await render_clan_card(bot, callback.message.chat.id, session, member, old_message=callback.message)


# --- Создание клана ---


@router.callback_query(F.data == CB_CLAN_CREATE_START)
async def cb_create_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ClanStates.waiting_clan_name)
    await callback.answer()
    await safe_edit_text(
        callback.message,
        CREATE_CLAN_PROMPT.format(min=CLAN_NAME_MIN_LENGTH, max=CLAN_NAME_MAX_LENGTH),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[]),
    )


@router.message(StateFilter(ClanStates.waiting_clan_name), Command("cancel"))
async def cancel_create_clan(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ACTION_CANCELLED)


@router.message(StateFilter(ClanStates.waiting_clan_name))
async def apply_create_clan(
    message: Message, state: FSMContext, session: AsyncSession, redis: Redis, bot: Bot
) -> None:
    name = (message.text or "").strip()
    if not (CLAN_NAME_MIN_LENGTH <= len(name) <= CLAN_NAME_MAX_LENGTH) or "\n" in name:
        await message.answer(CREATE_CLAN_INVALID.format(min=CLAN_NAME_MIN_LENGTH, max=CLAN_NAME_MAX_LENGTH))
        return

    user_id = message.from_user.id
    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_CREATE_CLAN)) as acquired:
        if not acquired:
            return

        try:
            await clan_service.create_clan(session, name=name, owner_id=user_id)
        except clan_service.ClanNameTakenError:
            await message.answer(CREATE_CLAN_TAKEN)
            return
        except clan_service.AlreadyInClanError:
            await state.clear()
            await message.answer(CREATE_CLAN_ALREADY_IN_CLAN)
            return

    await state.clear()
    await message.answer(CREATE_CLAN_DONE.format(name=name))
    member = await clan_repo.get_member(session, user_id)
    await render_clan_card(bot, message.chat.id, session, member)


# --- Поиск клана ---


@router.callback_query(F.data == CB_CLAN_FIND)
async def cb_find_clans(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    text, keyboard = await _render_find_page(session, 0)
    await safe_edit_text(callback.message, text, reply_markup=keyboard)


@router.callback_query(F.data.startswith(CB_CLAN_FIND_PAGE_PREFIX))
async def cb_find_clans_page(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    page = int(callback.data[len(CB_CLAN_FIND_PAGE_PREFIX) :])
    text, keyboard = await _render_find_page(session, page)
    await safe_edit_text(callback.message, text, reply_markup=keyboard)


@router.callback_query(F.data.startswith(CB_CLAN_VIEW_PREFIX))
async def cb_view_clan(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    clan_id = int(callback.data[len(CB_CLAN_VIEW_PREFIX) :])
    await callback.answer()
    await render_view_page(bot, callback.message.chat.id, callback.message, session, clan_id, callback.from_user.id)


@router.callback_query(F.data.startswith(CB_CLAN_APPLY_PREFIX))
async def cb_apply_clan(callback: CallbackQuery, session: AsyncSession, redis: Redis, bot: Bot) -> None:
    clan_id = int(callback.data[len(CB_CLAN_APPLY_PREFIX) :])
    user_id = callback.from_user.id
    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_APPLY_CLAN)) as acquired:
        if not acquired:
            await callback.answer()
            return

        try:
            await clan_service.apply_to_clan(session, clan_id=clan_id, user_id=user_id)
        except clan_service.AlreadyInClanError:
            await callback.answer(CREATE_CLAN_ALREADY_IN_CLAN, show_alert=True)
            return
        except clan_service.AlreadyAppliedElsewhereError:
            await callback.answer(ALREADY_APPLIED_ELSEWHERE, show_alert=True)
            return
        except clan_service.ClanNotFoundError:
            await callback.answer()
            return
        await callback.answer()

    view = await render_view_page(bot, callback.message.chat.id, callback.message, session, clan_id, user_id)
    if view is None:
        return

    owner = await get_user_by_id(session, view.clan.owner_id)
    if owner is not None and owner.notify_clan_requests:
        username = callback.from_user.username or str(user_id)
        await notify(bot, owner.id, NOTIFY_NEW_APPLICATION.format(username=username, clan_name=view.clan.name))


@router.callback_query(F.data.startswith(CB_CLAN_CANCEL_APPLICATION_PREFIX))
async def cb_cancel_application(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    clan_id = int(callback.data[len(CB_CLAN_CANCEL_APPLICATION_PREFIX) :])
    user_id = callback.from_user.id
    await clan_service.cancel_application(session, clan_id=clan_id, user_id=user_id)
    await callback.answer()
    await render_view_page(bot, callback.message.chat.id, callback.message, session, clan_id, user_id)


# --- Участники ---


@router.callback_query(F.data == CB_CLAN_MEMBERS)
async def cb_members(callback: CallbackQuery, session: AsyncSession) -> None:
    member = await clan_repo.get_member(session, callback.from_user.id)
    if member is None:
        await callback.answer(NOT_IN_CLAN, show_alert=True)
        return
    await callback.answer()

    clan = await clan_repo.get_by_id(session, member.clan_id)
    rows = await clan_service.list_members_with_users(session, member.clan_id)
    lines = "".join(
        MEMBERS_LINE.format(
            rank_emoji=RANK_EMOJI[m.rank.value],
            name=u.display_name,
            username=u.username or "—",
            rank_name=RANK_NAME[m.rank.value],
        )
        for m, u in rows
    )
    text = MEMBERS_HEADER.format(name=clan.name if clan else "") + lines
    await safe_edit_text(callback.message, text, reply_markup=back_to_clan_menu())


# --- Выход из клана ---


@router.callback_query(F.data == CB_CLAN_LEAVE)
async def cb_leave_start(callback: CallbackQuery, session: AsyncSession) -> None:
    member = await clan_repo.get_member(session, callback.from_user.id)
    if member is None:
        await callback.answer(NOT_IN_CLAN, show_alert=True)
        return
    if member.rank == ClanRank.owner:
        await callback.answer(LEAVE_MUST_TRANSFER, show_alert=True)
        return
    await callback.answer()

    clan = await clan_repo.get_by_id(session, member.clan_id)
    await safe_edit_text(
        callback.message, LEAVE_CONFIRM.format(name=clan.name if clan else ""), reply_markup=leave_confirm_menu()
    )


@router.callback_query(F.data == CB_CLAN_LEAVE_CONFIRM)
async def cb_leave_confirm(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    user_id = callback.from_user.id
    try:
        await clan_service.leave_clan(session, user_id=user_id)
    except clan_service.NotInClanError:
        await callback.answer(NOT_IN_CLAN, show_alert=True)
        return
    except clan_service.MustTransferOwnershipFirstError:
        await callback.answer(LEAVE_MUST_TRANSFER, show_alert=True)
        return

    await callback.answer(LEAVE_DONE, show_alert=True)
    await render_no_clan_screen(bot, callback.message.chat.id, callback.message, session, user_id)
