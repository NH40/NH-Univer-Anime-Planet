from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    waiting_find_player = State()
    waiting_give_dust = State()
    waiting_give_coins = State()
    waiting_give_card = State()
    waiting_give_ticket_cap_seasonal = State()
    waiting_give_ticket_cap_permanent = State()
    waiting_give_subscription = State()
    waiting_new_season_version = State()
    waiting_bump_version = State()
    waiting_promo_create = State()
    waiting_referral_create = State()
    waiting_broadcast_text = State()
    waiting_mass_grant_amount = State()
    waiting_delete_account = State()
    waiting_manage_admin_search = State()
