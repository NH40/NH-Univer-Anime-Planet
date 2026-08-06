from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.game import DAILY_BONUS_MAX_STREAK, daily_bonus_reward
from bot.constant.daily_bonus import CB_DAILY_BONUS_CLAIM
from bot.constant.profile import CB_PROFILE_DAILY_BONUS
from bot.keyboards.daily_bonus import daily_bonus_menu
from bot.services import daily_bonus as daily_bonus_service
from bot.texts.common import NEED_START
from bot.texts.daily_bonus import (
    CELL_DONE,
    CELL_FUTURE,
    CELL_READY,
    CLAIM_ALREADY,
    CLAIM_DONE,
    DAILY_BONUS_SCREEN,
    STATUS_COUNTDOWN,
    STATUS_READY,
    STATUS_READY_RESET,
)
from bot.utils.safe_edit import safe_edit_text

router = Router(name="daily_bonus")


def _cells(status: daily_bonus_service.DailyBonusStatus) -> str:
    # Пропущенный день — показываем серию как ещё не начатую (0 отмеченных), чтобы визуально
    # не обещать день N+1, который на самом деле сбросится на 1 при сборе (см. get_status).
    confirmed = 0 if status.resets_on_claim else status.streak
    cells = []
    for day in range(1, DAILY_BONUS_MAX_STREAK + 1):
        if day <= confirmed:
            cells.append(CELL_DONE)
        elif day == confirmed + 1 and status.claimable:
            cells.append(CELL_READY)
        else:
            cells.append(CELL_FUTURE)
    return " ".join(cells)


def _render(status: daily_bonus_service.DailyBonusStatus) -> str:
    confirmed = 0 if status.resets_on_claim else status.streak
    next_day = min(confirmed + 1, DAILY_BONUS_MAX_STREAK)
    dust, tickets = daily_bonus_reward(next_day)

    if status.claimable:
        status_line = STATUS_READY_RESET if status.resets_on_claim else STATUS_READY
    else:
        mm, ss = divmod(status.seconds_until_claimable or 0, 60)
        status_line = STATUS_COUNTDOWN.format(mm=mm, ss=ss)

    return DAILY_BONUS_SCREEN.format(cells=_cells(status), status_line=status_line, day=next_day, dust=dust, tickets=tickets)


@router.callback_query(F.data == CB_PROFILE_DAILY_BONUS)
async def cb_open_daily_bonus(callback: CallbackQuery, session: AsyncSession) -> None:
    status = await daily_bonus_service.get_status(session, callback.from_user.id)
    await callback.answer()
    if status is None:
        await callback.message.answer(NEED_START)
        return
    await safe_edit_text(callback.message, _render(status), reply_markup=daily_bonus_menu(claimable=status.claimable))


@router.callback_query(F.data == CB_DAILY_BONUS_CLAIM)
async def cb_claim_daily_bonus(callback: CallbackQuery, session: AsyncSession) -> None:
    try:
        result = await daily_bonus_service.claim(session, user_id=callback.from_user.id)
    except daily_bonus_service.AlreadyClaimedError:
        await callback.answer(CLAIM_ALREADY, show_alert=True)
        return

    await callback.answer(CLAIM_DONE.format(day=result.day, dust=result.dust, tickets=result.tickets), show_alert=True)

    status = await daily_bonus_service.get_status(session, callback.from_user.id)
    if status is not None:
        await safe_edit_text(
            callback.message, _render(status), reply_markup=daily_bonus_menu(claimable=status.claimable)
        )
