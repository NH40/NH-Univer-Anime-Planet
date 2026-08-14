from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class DustStates(StatesGroup):
    # tier/card_id/stars текущей стопки кладутся в state data через update_data() перед
    # входом в это состояние (см. handlers/dust) — тот же паттерн, что у shop's "своё число".
    waiting_amount = State()
