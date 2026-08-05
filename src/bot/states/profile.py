from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class ProfileStates(StatesGroup):
    waiting_new_name = State()
