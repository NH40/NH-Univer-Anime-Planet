from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.constant.promo import CB_PROMO_REDEEM_CANCEL
from bot.db.repositories.user import get_by_id
from bot.keyboards.promo import redeem_prompt_menu
from bot.services import promo as promo_service
from bot.states.promo import PromoStates
from bot.texts.admin import (
    ACTION_CANCELLED,
    PROMO_ALREADY_REDEEMED,
    PROMO_EXPIRED,
    PROMO_NOT_ALLOWED,
    PROMO_NOT_FOUND,
    PROMO_REDEEM_DONE,
    PROMO_REDEEM_PROMPT,
    PROMO_USES_EXHAUSTED,
)
from bot.texts.common import NEED_START
from bot.utils.safe_edit import safe_edit_text

router = Router(name="promo")


async def _redeem_and_reply(message: Message, session: AsyncSession, code: str) -> None:
    try:
        reward = await promo_service.redeem(
            session, code=code.strip().upper(), user_id=message.from_user.id, username=message.from_user.username
        )
    except promo_service.PromoNotFoundError:
        await message.answer(PROMO_NOT_FOUND)
        return
    except promo_service.PromoExpiredError:
        await message.answer(PROMO_EXPIRED)
        return
    except promo_service.PromoNotAllowedError:
        await message.answer(PROMO_NOT_ALLOWED)
        return
    except promo_service.PromoUsesExhaustedError:
        await message.answer(PROMO_USES_EXHAUSTED)
        return
    except promo_service.PromoAlreadyRedeemedError:
        await message.answer(PROMO_ALREADY_REDEEMED)
        return

    await message.answer(
        PROMO_REDEEM_DONE.format(dust=reward["dust"], coins=reward["coins"], tickets=reward["tickets"])
    )


@router.message(Command("promo"))
async def cmd_promo(message: Message, command: CommandObject, state: FSMContext, session: AsyncSession) -> None:
    user = await get_by_id(session, message.from_user.id)
    if user is None:
        await message.answer(NEED_START)
        return

    code = (command.args or "").strip()
    if not code:
        await state.set_state(PromoStates.waiting_code)
        await message.answer(PROMO_REDEEM_PROMPT, reply_markup=redeem_prompt_menu())
        return

    await _redeem_and_reply(message, session, code)


@router.message(StateFilter(PromoStates.waiting_code), Command("cancel"))
async def cancel_promo_redeem(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ACTION_CANCELLED)


@router.callback_query(StateFilter(PromoStates.waiting_code), F.data == CB_PROMO_REDEEM_CANCEL)
async def cb_cancel_promo_redeem(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    # Явно чистим клавиатуру — edit_text без reply_markup её сохраняет, не убирает
    # (см. CLAUDE.md, правило 11).
    await safe_edit_text(callback.message, ACTION_CANCELLED, reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))


@router.message(StateFilter(PromoStates.waiting_code))
async def apply_promo_redeem(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    await _redeem_and_reply(message, session, (message.text or "").strip())
