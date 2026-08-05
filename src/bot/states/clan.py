from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class ClanStates(StatesGroup):
    waiting_clan_name = State()
    waiting_invite_username = State()
    waiting_edit_name = State()
    waiting_edit_description = State()
    waiting_edit_image = State()
    waiting_exchange_input = State()
