from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.constant.admin import CB_ADMIN_PROMO, CB_ADMIN_PROMO_CREATE
from bot.db.models.enums import PromoCodeType
from bot.keyboards.admin import promo_create_prompt_menu, promo_menu
from bot.services import promo as promo_service
from bot.states.admin import AdminStates
from bot.texts.admin import (
    ACTION_CANCELLED,
    PROMO_CREATE_DONE,
    PROMO_CREATE_INVALID,
    PROMO_CREATE_PROMPT,
    PROMO_CREATE_TAKEN,
    PROMO_LINE,
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


def _reward_line(status: promo_service.PromoStatus) -> str:
    parts = []
    if status.dust:
        parts.append(f"{status.dust}✨")
    if status.coins:
        parts.append(f"{status.coins}💎")
    if status.tickets:
        parts.append(f"{status.tickets}🎫")
    reward = ", ".join(parts) if parts else "—"
    uses = PROMO_LINE_USES.format(used=status.used_count, max_uses=status.max_uses) if status.max_uses is not None else ""
    return PROMO_LINE.format(
        icon=PROMO_LINE_ACTIVE if status.is_active else PROMO_LINE_INACTIVE, code=status.code, reward=reward, uses=uses
    )


async def _render_promo_screen(session: AsyncSession) -> str:
    statuses = await promo_service.list_status(session)
    lines = "".join(_reward_line(s) for s in statuses) if statuses else PROMO_SCREEN_EMPTY
    return PROMO_SCREEN.format(count=len(statuses), lines=lines)


@router.callback_query(F.data == CB_ADMIN_PROMO)
async def cb_promo(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    # На случай прихода сюда как "Назад" из waiting_promo_create — иначе FSM-состояние
    # осталось бы висеть, и следующий текст игрока ошибочно попал бы в apply_promo_create.
    await state.clear()
    await callback.answer()
    text = await _render_promo_screen(session)
    await safe_edit_text(callback.message, text, reply_markup=promo_menu())


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
    lines = [line.strip() for line in (message.text or "").split("\n") if line.strip()]
    if len(lines) != 4:
        await message.answer(PROMO_CREATE_INVALID)
        return

    code, type_str, param, reward_str = lines
    code = code.upper()
    type_enum = _TYPES.get(type_str.lower())
    reward_parts = reward_str.split()

    if not _CODE_RE.match(code) or type_enum is None or len(reward_parts) != 3 or not all(p.isdigit() for p in reward_parts):
        await message.answer(PROMO_CREATE_INVALID)
        return

    dust, coins, tickets = (int(p) for p in reward_parts)

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
        expires_at = datetime.now(timezone.utc) + timedelta(days=int(param))
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
            dust=dust,
            coins=coins,
            tickets=tickets,
        )
    except promo_service.PromoTakenError:
        await message.answer(PROMO_CREATE_TAKEN)
        return

    await message.answer(PROMO_CREATE_DONE.format(code=code))
    text = await _render_promo_screen(session)
    await message.answer(text, reply_markup=promo_menu())
