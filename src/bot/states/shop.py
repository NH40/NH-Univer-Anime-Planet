from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class ShopStates(StatesGroup):
    waiting_ticket_quantity = State()
    # Одно состояние на весь флоу "ввели число -> показали цену -> подтвердите": пока ждём
    # подтверждения, это по-прежнему то же состояние (данные — в state data), а не отдельное
    # "waiting_confirm" — коллбэк подтверждения не гейтится фильтром по состоянию.
    waiting_coin_ticket_quantity = State()
    # "Своё число" слотов капа тикетов — kind (seasonal/permanent) хранится в state data
    # (см. handlers/shop.cb_start_ticket_cap_custom), состояние очищается сразу после ввода
    # числа (подтверждение — уже отдельный callback без гейта по состоянию, как и выше).
    waiting_ticket_cap_quantity = State()
