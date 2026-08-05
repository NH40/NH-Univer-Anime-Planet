from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class CasinoStates(StatesGroup):
    waiting_mass_roll_quantity = State()
