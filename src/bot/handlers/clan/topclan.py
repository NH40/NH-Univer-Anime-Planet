from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.constant.clan import CB_TOPCLAN_PAGE_PREFIX, CB_TOPCLAN_TOGGLE_PREFIX
from bot.handlers.clan.clan import CLAN_PAGE_SIZE
from bot.keyboards.clan import topclan_menu
from bot.services import clan as clan_service
from bot.texts.clan import FIND_CLANS_EMPTY, FIND_CLANS_LINE, TOPCLAN_HEADER, TOPCLAN_MODE_SEASON, TOPCLAN_MODE_TOTAL
from bot.utils.formatting import format_number
from bot.utils.safe_edit import safe_edit_text

router = Router(name="topclan")


async def _render_topclan(session: AsyncSession, page: int, by_total: bool) -> tuple[str, InlineKeyboardMarkup]:
    mode = TOPCLAN_MODE_TOTAL if by_total else TOPCLAN_MODE_SEASON
    rows, total_pages = await clan_service.browse_clans(session, by_total=by_total, page=page, page_size=CLAN_PAGE_SIZE)

    if not rows:
        text = TOPCLAN_HEADER.format(mode=mode, page=1, total_pages=1) + FIND_CLANS_EMPTY
        return text, topclan_menu(page=0, total_pages=1, by_total=by_total)

    offset = page * CLAN_PAGE_SIZE
    lines = "".join(
        FIND_CLANS_LINE.format(place=offset + i + 1, name=clan.name, ubp=format_number(ubp), members=cnt)
        for i, (clan, ubp, cnt) in enumerate(rows)
    )
    text = TOPCLAN_HEADER.format(mode=mode, page=page + 1, total_pages=total_pages) + lines
    return text, topclan_menu(page=page, total_pages=total_pages, by_total=by_total)


@router.message(Command("topclan"))
async def show_topclan(message: Message, session: AsyncSession) -> None:
    text, keyboard = await _render_topclan(session, 0, by_total=False)
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith(CB_TOPCLAN_PAGE_PREFIX))
async def cb_topclan_page(callback: CallbackQuery, session: AsyncSession) -> None:
    page_str, mode_str = callback.data[len(CB_TOPCLAN_PAGE_PREFIX) :].split(":")
    await callback.answer()
    text, keyboard = await _render_topclan(session, int(page_str), by_total=bool(int(mode_str)))
    await safe_edit_text(callback.message, text, reply_markup=keyboard)


@router.callback_query(F.data.startswith(CB_TOPCLAN_TOGGLE_PREFIX))
async def cb_topclan_toggle(callback: CallbackQuery, session: AsyncSession) -> None:
    current_by_total = bool(int(callback.data[len(CB_TOPCLAN_TOGGLE_PREFIX) :]))
    await callback.answer()
    text, keyboard = await _render_topclan(session, 0, by_total=not current_by_total)
    await safe_edit_text(callback.message, text, reply_markup=keyboard)
