from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.game import CLAN_DESCRIPTION_MAX_LENGTH, CLAN_NAME_MAX_LENGTH, CLAN_NAME_MIN_LENGTH, CLAN_TOP_IMAGE_ELIGIBLE_COUNT
from bot.constant.clan import CB_CLAN_EDIT, CB_CLAN_EDIT_DESCRIPTION, CB_CLAN_EDIT_IMAGE, CB_CLAN_EDIT_NAME
from bot.db.repositories import clan as clan_repo
from bot.keyboards.clan import edit_menu
from bot.services import clan as clan_service
from bot.states.clan import ClanStates
from bot.texts.clan import (
    ACTION_CANCELLED,
    CREATE_CLAN_INVALID,
    CREATE_CLAN_TAKEN,
    EDIT_DESCRIPTION_DONE,
    EDIT_DESCRIPTION_PROMPT,
    EDIT_DESCRIPTION_TOO_LONG,
    EDIT_IMAGE_DONE,
    EDIT_IMAGE_NOT_ELIGIBLE,
    EDIT_IMAGE_PROMPT,
    EDIT_MENU,
    EDIT_NAME_DONE,
    EDIT_NAME_PROMPT,
    NOT_AUTHORIZED,
)
from bot.utils.safe_edit import safe_edit_text

router = Router(name="clan_edit")


@router.callback_query(F.data == CB_CLAN_EDIT)
async def cb_edit_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    member = await clan_repo.get_member(session, callback.from_user.id)
    if member is None or member.rank not in clan_service.MANAGER_RANKS:
        await callback.answer(NOT_AUTHORIZED, show_alert=True)
        return
    await callback.answer()

    top_ids = await clan_repo.list_top_all_time_ids(session, limit=CLAN_TOP_IMAGE_ELIGIBLE_COUNT)
    await safe_edit_text(callback.message, EDIT_MENU, reply_markup=edit_menu(can_set_image=member.clan_id in top_ids))


# --- Название ---


@router.callback_query(F.data == CB_CLAN_EDIT_NAME)
async def cb_edit_name_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    member = await clan_repo.get_member(session, callback.from_user.id)
    if member is None or member.rank not in clan_service.MANAGER_RANKS:
        await callback.answer(NOT_AUTHORIZED, show_alert=True)
        return
    await state.set_state(ClanStates.waiting_edit_name)
    await callback.answer()
    await safe_edit_text(
        callback.message,
        EDIT_NAME_PROMPT.format(min=CLAN_NAME_MIN_LENGTH, max=CLAN_NAME_MAX_LENGTH),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[]),
    )


@router.message(StateFilter(ClanStates.waiting_edit_name), Command("cancel"))
async def cancel_edit_name(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ACTION_CANCELLED)


@router.message(StateFilter(ClanStates.waiting_edit_name))
async def apply_edit_name(message: Message, state: FSMContext, session: AsyncSession) -> None:
    name = (message.text or "").strip()
    if not (CLAN_NAME_MIN_LENGTH <= len(name) <= CLAN_NAME_MAX_LENGTH) or "\n" in name:
        await message.answer(CREATE_CLAN_INVALID.format(min=CLAN_NAME_MIN_LENGTH, max=CLAN_NAME_MAX_LENGTH))
        return
    await state.clear()

    member = await clan_repo.get_member(session, message.from_user.id)
    if member is None or member.rank not in clan_service.MANAGER_RANKS:
        await message.answer(NOT_AUTHORIZED)
        return

    try:
        await clan_service.edit_profile(session, clan_id=member.clan_id, actor_id=message.from_user.id, name=name)
    except clan_service.ClanNameTakenError:
        await message.answer(CREATE_CLAN_TAKEN)
        return
    except clan_service.NotAuthorizedError:
        await message.answer(NOT_AUTHORIZED)
        return
    await message.answer(EDIT_NAME_DONE)


# --- Описание ---


@router.callback_query(F.data == CB_CLAN_EDIT_DESCRIPTION)
async def cb_edit_description_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    member = await clan_repo.get_member(session, callback.from_user.id)
    if member is None or member.rank not in clan_service.MANAGER_RANKS:
        await callback.answer(NOT_AUTHORIZED, show_alert=True)
        return
    await state.set_state(ClanStates.waiting_edit_description)
    await callback.answer()
    await safe_edit_text(
        callback.message,
        EDIT_DESCRIPTION_PROMPT.format(max=CLAN_DESCRIPTION_MAX_LENGTH),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[]),
    )


@router.message(StateFilter(ClanStates.waiting_edit_description), Command("cancel"))
async def cancel_edit_description(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ACTION_CANCELLED)


@router.message(StateFilter(ClanStates.waiting_edit_description))
async def apply_edit_description(message: Message, state: FSMContext, session: AsyncSession) -> None:
    description = (message.text or "").strip()
    if len(description) > CLAN_DESCRIPTION_MAX_LENGTH:
        await message.answer(EDIT_DESCRIPTION_TOO_LONG.format(max=CLAN_DESCRIPTION_MAX_LENGTH))
        return
    await state.clear()

    member = await clan_repo.get_member(session, message.from_user.id)
    if member is None or member.rank not in clan_service.MANAGER_RANKS:
        await message.answer(NOT_AUTHORIZED)
        return

    try:
        await clan_service.edit_profile(
            session, clan_id=member.clan_id, actor_id=message.from_user.id, description=description
        )
    except clan_service.NotAuthorizedError:
        await message.answer(NOT_AUTHORIZED)
        return
    await message.answer(EDIT_DESCRIPTION_DONE)


# --- Картинка (доступно только топ-10 кланам по UBP за всё время) ---


@router.callback_query(F.data == CB_CLAN_EDIT_IMAGE)
async def cb_edit_image_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    member = await clan_repo.get_member(session, callback.from_user.id)
    if member is None or member.rank not in clan_service.MANAGER_RANKS:
        await callback.answer(NOT_AUTHORIZED, show_alert=True)
        return
    top_ids = await clan_repo.list_top_all_time_ids(session, limit=CLAN_TOP_IMAGE_ELIGIBLE_COUNT)
    if member.clan_id not in top_ids:
        await callback.answer(EDIT_IMAGE_NOT_ELIGIBLE.format(n=CLAN_TOP_IMAGE_ELIGIBLE_COUNT), show_alert=True)
        return

    await state.set_state(ClanStates.waiting_edit_image)
    await callback.answer()
    await safe_edit_text(callback.message, EDIT_IMAGE_PROMPT, reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))


@router.message(StateFilter(ClanStates.waiting_edit_image), Command("cancel"))
async def cancel_edit_image(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ACTION_CANCELLED)


@router.message(StateFilter(ClanStates.waiting_edit_image), F.photo)
async def apply_edit_image(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    member = await clan_repo.get_member(session, message.from_user.id)
    if member is None or member.rank not in clan_service.MANAGER_RANKS:
        await message.answer(NOT_AUTHORIZED)
        return

    # Telegram file_id, а не локальный путь — в отличие от карточек персонажей, картинку
    # клана присылает сам игрок в чат, у бота нет пайплайна сохранения таких файлов на диск.
    file_id = message.photo[-1].file_id
    try:
        await clan_service.set_image(session, clan_id=member.clan_id, actor_id=message.from_user.id, image_path=file_id)
    except clan_service.NotAuthorizedError:
        await message.answer(EDIT_IMAGE_NOT_ELIGIBLE.format(n=CLAN_TOP_IMAGE_ELIGIBLE_COUNT))
        return
    await message.answer(EDIT_IMAGE_DONE)


@router.message(StateFilter(ClanStates.waiting_edit_image))
async def apply_edit_image_invalid(message: Message) -> None:
    await message.answer(EDIT_IMAGE_PROMPT)
