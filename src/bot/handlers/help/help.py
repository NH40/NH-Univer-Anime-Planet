from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.config.help import HELP_SECTIONS_BY_CODE
from bot.constant.help import CB_HELP_OPEN, CB_HELP_SECTION_PREFIX
from bot.keyboards.help import help_menu, help_section_menu
from bot.texts.common import UNKNOWN_CALLBACK
from bot.texts.help import HELP_MENU
from bot.utils.safe_edit import safe_edit_text

router = Router(name="help")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_MENU, reply_markup=help_menu())


@router.callback_query(F.data == CB_HELP_OPEN)
async def cb_help_open(callback: CallbackQuery) -> None:
    await callback.answer()
    await safe_edit_text(callback.message, HELP_MENU, reply_markup=help_menu())


@router.callback_query(F.data.startswith(CB_HELP_SECTION_PREFIX))
async def cb_help_section(callback: CallbackQuery) -> None:
    code = callback.data[len(CB_HELP_SECTION_PREFIX) :]
    section = HELP_SECTIONS_BY_CODE.get(code)
    if section is None:
        await callback.answer(UNKNOWN_CALLBACK, show_alert=True)
        return

    await callback.answer()
    await safe_edit_text(
        callback.message, f"{section.title}\n\n{section.body}", reply_markup=help_section_menu()
    )
