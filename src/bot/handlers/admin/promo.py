from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.constant.admin import (
    CB_ADMIN_PROMO,
    CB_ADMIN_PROMO_CREATE,
    CB_ADMIN_PROMO_DELETE_CONFIRM_PREFIX,
    CB_ADMIN_PROMO_DELETE_PREFIX,
    CB_ADMIN_PROMO_DETAIL_PREFIX,
    CB_ADMIN_PROMO_TOGGLE_PREFIX,
)
from bot.db.models.enums import PromoCodeType
from bot.keyboards.admin import promo_create_prompt_menu, promo_delete_confirm_menu, promo_detail_menu, promo_menu
from bot.services import promo as promo_service
from bot.states.admin import AdminStates
from bot.texts.admin import (
    ACTION_CANCELLED,
    PROMO_ACTIVATE_DONE,
    PROMO_CREATE_DONE,
    PROMO_CREATE_INVALID,
    PROMO_CREATE_PROMPT,
    PROMO_CREATE_TAKEN,
    PROMO_DEACTIVATE_DONE,
    PROMO_DELETE_CONFIRM,
    PROMO_DELETE_DONE,
    PROMO_DETAIL,
    PROMO_DETAIL_STATUS_ACTIVE,
    PROMO_DETAIL_STATUS_INACTIVE,
    PROMO_DETAIL_USES_LINE,
    PROMO_LINE_ACTIVE,
    PROMO_LINE_INACTIVE,
    PROMO_LINE_USES,
    PROMO_SCREEN,
    PROMO_SCREEN_EMPTY,
)
from bot.utils.safe_edit import safe_edit_text

router = Router(name="admin_promo")

_CODE_RE = re.compile(r"^[A-Za-z0-9]{1,32}$")
_TYPES = {"uses": PromoCodeType.uses, "time": PromoCodeType.time, "users": PromoCodeType.user_list}
# Только валюты, которые реально существуют в этой игре (см. CLAUDE.md, "Промокоды:
# многострочный ввод -> одна строка с несколькими наградами" — формат-пример, присланный
# пользователем 2026-08-14, включал фрагменты/очки мастерства и т.п. из другого проекта,
# в этой игре их нет, добавлять не стали).
_REWARD_TOKEN_RE = re.compile(r"^(tickets|coins|dust):(-?\d+)$")


def _reward_summary(status: promo_service.PromoStatus) -> str:
    """Плоская строка без HTML (переиспользуется и в тексте сообщения, и в тексте кнопки
    списка — у кнопки HTML не рендерится вообще, см. CLAUDE.md, "Popup-алерты не
    поддерживают HTML" — тот же принцип: plain-text поверхность требует plain-text строку)."""
    parts = []
    if status.dust:
        parts.append(f"{status.dust}✨")
    if status.coins:
        parts.append(f"{status.coins}💎")
    if status.tickets:
        parts.append(f"{status.tickets}🎫")
    return ", ".join(parts) if parts else "—"


def _button_label(status: promo_service.PromoStatus) -> str:
    icon = PROMO_LINE_ACTIVE if status.is_active else PROMO_LINE_INACTIVE
    uses = PROMO_LINE_USES.format(used=status.used_count, max_uses=status.max_uses) if status.max_uses is not None else ""
    return f"{icon} {status.code} | {_reward_summary(status)}{uses}"


async def _render_promo_screen(session: AsyncSession) -> tuple[str, list[tuple[str, str]]]:
    statuses = await promo_service.list_status(session)
    codes = [(s.code, _button_label(s)) for s in statuses]
    text = PROMO_SCREEN.format(count=len(statuses), lines="" if statuses else PROMO_SCREEN_EMPTY)
    return text, codes


def _render_detail_text(status: promo_service.PromoStatus) -> str:
    uses_line = (
        PROMO_DETAIL_USES_LINE.format(used=status.used_count, max_uses=status.max_uses)
        if status.max_uses is not None
        else ""
    )
    status_label = PROMO_DETAIL_STATUS_ACTIVE if status.is_active else PROMO_DETAIL_STATUS_INACTIVE
    return PROMO_DETAIL.format(code=status.code, status=status_label, reward=_reward_summary(status), uses_line=uses_line)


@router.callback_query(F.data == CB_ADMIN_PROMO)
async def cb_promo(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    # На случай прихода сюда как "Назад" из waiting_promo_create — иначе FSM-состояние
    # осталось бы висеть, и следующий текст игрока ошибочно попал бы в apply_promo_create.
    await state.clear()
    await callback.answer()
    text, codes = await _render_promo_screen(session)
    await safe_edit_text(callback.message, text, reply_markup=promo_menu(codes))


@router.callback_query(F.data == CB_ADMIN_PROMO_CREATE)
async def cb_promo_create_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_promo_create)
    await callback.answer()
    await safe_edit_text(callback.message, PROMO_CREATE_PROMPT, reply_markup=promo_create_prompt_menu())


@router.message(StateFilter(AdminStates.waiting_promo_create), Command("cancel"))
async def cancel_promo_create(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ACTION_CANCELLED)


@router.message(StateFilter(AdminStates.waiting_promo_create))
async def apply_promo_create(message: Message, state: FSMContext, session: AsyncSession) -> None:
    # Одна строка: КОД [uses|time|users] ПАРАМ НАГРАДА1:КОЛ НАГРАДА2:КОЛ ... (переработано
    # 2026-08-14 по запросу пользователя — было 4 строки, ровно один тип награды каждая).
    parts = (message.text or "").split()
    if len(parts) < 4:
        await message.answer(PROMO_CREATE_INVALID)
        return

    code = parts[0].upper()
    type_enum = _TYPES.get(parts[1].lower())
    param = parts[2]

    if not _CODE_RE.match(code) or type_enum is None:
        await message.answer(PROMO_CREATE_INVALID)
        return

    reward: dict[str, int] = {}
    for token in parts[3:]:
        match = _REWARD_TOKEN_RE.match(token)
        if match is None:
            await message.answer(PROMO_CREATE_INVALID)
            return
        key, amount = match.group(1), int(match.group(2))
        reward[key] = reward.get(key, 0) + amount
    if not any(reward.values()):
        await message.answer(PROMO_CREATE_INVALID)
        return

    max_uses: int | None = None
    expires_at: datetime | None = None
    allowed_usernames: list[str] | None = None

    if type_enum is PromoCodeType.uses:
        if not param.isdigit() or int(param) <= 0:
            await message.answer(PROMO_CREATE_INVALID)
            return
        max_uses = int(param)
    elif type_enum is PromoCodeType.time:
        if not param.isdigit() or int(param) <= 0:
            await message.answer(PROMO_CREATE_INVALID)
            return
        # Часы, не дни (изменено 2026-08-14 по запросу пользователя — раньше параметр time
        # значил "дней действия").
        expires_at = datetime.now(timezone.utc) + timedelta(hours=int(param))
    else:
        allowed_usernames = [u.strip().lstrip("@") for u in param.split(",") if u.strip()]
        if not allowed_usernames:
            await message.answer(PROMO_CREATE_INVALID)
            return

    await state.clear()

    try:
        await promo_service.create_promo(
            session,
            code=code,
            type_=type_enum,
            max_uses=max_uses,
            expires_at=expires_at,
            allowed_usernames=allowed_usernames,
            reward=reward,
        )
    except promo_service.PromoTakenError:
        await message.answer(PROMO_CREATE_TAKEN)
        return

    await message.answer(PROMO_CREATE_DONE.format(code=code))
    text, codes = await _render_promo_screen(session)
    await message.answer(text, reply_markup=promo_menu(codes))


@router.callback_query(F.data.startswith(CB_ADMIN_PROMO_DETAIL_PREFIX))
async def cb_promo_detail(callback: CallbackQuery, session: AsyncSession) -> None:
    code = callback.data[len(CB_ADMIN_PROMO_DETAIL_PREFIX) :]
    status = await promo_service.get_status(session, code=code)
    await callback.answer()
    if status is None:
        text, codes = await _render_promo_screen(session)
        await safe_edit_text(callback.message, text, reply_markup=promo_menu(codes))
        return
    await safe_edit_text(
        callback.message, _render_detail_text(status), reply_markup=promo_detail_menu(code=code, is_active=status.is_active)
    )


@router.callback_query(F.data.startswith(CB_ADMIN_PROMO_TOGGLE_PREFIX))
async def cb_promo_toggle(callback: CallbackQuery, session: AsyncSession) -> None:
    code = callback.data[len(CB_ADMIN_PROMO_TOGGLE_PREFIX) :]
    status = await promo_service.get_status(session, code=code)
    if status is None:
        await callback.answer()
        text, codes = await _render_promo_screen(session)
        await safe_edit_text(callback.message, text, reply_markup=promo_menu(codes))
        return

    if status.is_active:
        await promo_service.deactivate_promo(session, code=code)
        await callback.answer(PROMO_DEACTIVATE_DONE.format(code=code))
    else:
        await promo_service.activate_promo(session, code=code)
        await callback.answer(PROMO_ACTIVATE_DONE.format(code=code))

    new_status = await promo_service.get_status(session, code=code)
    await safe_edit_text(
        callback.message,
        _render_detail_text(new_status),
        reply_markup=promo_detail_menu(code=code, is_active=new_status.is_active),
    )


@router.callback_query(F.data.startswith(CB_ADMIN_PROMO_DELETE_PREFIX))
async def cb_promo_delete_start(callback: CallbackQuery, session: AsyncSession) -> None:
    code = callback.data[len(CB_ADMIN_PROMO_DELETE_PREFIX) :]
    await callback.answer()
    await safe_edit_text(callback.message, PROMO_DELETE_CONFIRM.format(code=code), reply_markup=promo_delete_confirm_menu(code))


@router.callback_query(F.data.startswith(CB_ADMIN_PROMO_DELETE_CONFIRM_PREFIX))
async def cb_promo_delete_confirm(callback: CallbackQuery, session: AsyncSession) -> None:
    code = callback.data[len(CB_ADMIN_PROMO_DELETE_CONFIRM_PREFIX) :]
    try:
        await promo_service.delete_promo(session, code=code)
    except promo_service.PromoNotFoundError:
        pass
    await callback.answer(PROMO_DELETE_DONE.format(code=code), show_alert=True)

    text, codes = await _render_promo_screen(session)
    await safe_edit_text(callback.message, text, reply_markup=promo_menu(codes))
