from __future__ import annotations

TRANSACTION_REASON_ADMIN_GRANT_DUST = "admin_grant_dust"
TRANSACTION_REASON_ADMIN_GRANT_COINS = "admin_grant_coins"
TRANSACTION_REASON_ADMIN_MASS_GRANT = "admin_mass_grant"
TRANSACTION_REASON_PROMO = "promo_redeem"

CB_ADMIN_OPEN = "admin:open"
CB_ADMIN_TECH_MODE_TOGGLE = "admin:tech_toggle"
CB_ADMIN_STATS = "admin:stats"

CB_ADMIN_FIND_PLAYER_START = "admin:find_player"
CB_ADMIN_PLAYER_GIVE_DUST_PREFIX = "admin:give_dust:"
CB_ADMIN_PLAYER_GIVE_COINS_PREFIX = "admin:give_coins:"
CB_ADMIN_PLAYER_GIVE_CARD_PREFIX = "admin:give_card:"
# Слот капа тикетов (см. CLAUDE.md, "Магазин: слот капа тикетов") — та же выдача текстом
# числа, что give_dust/give_coins, только без Transaction (нет варианта "слот капа" в
# TransactionCurrency, тот же принцип, что у выдачи карточки — см. CLAUDE.md).
CB_ADMIN_PLAYER_GIVE_TICKET_CAP_SEASONAL_PREFIX = "admin:give_cap_s:"
CB_ADMIN_PLAYER_GIVE_TICKET_CAP_PERMANENT_PREFIX = "admin:give_cap_p:"
CB_ADMIN_PLAYER_BAN_TOGGLE_PREFIX = "admin:ban_toggle:"
CB_ADMIN_PLAYER_VIEW_PREFIX = "admin:player_view:"

# Выдача карточки — выбор вселенной/карты кнопками вместо ввода id карты вручную
# (подтверждено пользователем 2026-08-11: сырой числовой id было неудобно помнить/вводить).
# target_id/universe_code копятся в FSM-данных состояния (см. handlers/admin/admin.py) —
# в callback_data кодируется только то, что специфично для конкретного шага.
CB_ADMIN_GIVE_CARD_UNIVERSE_PREFIX = "admin:give_card_uni:"
CB_ADMIN_GIVE_CARD_PAGE_PREFIX = "admin:give_card_page:"
CB_ADMIN_GIVE_CARD_CARD_PREFIX = "admin:give_card_card:"

CB_ADMIN_SEASON = "admin:season"
CB_ADMIN_SEASON_NEW = "admin:season_new"
CB_ADMIN_SEASON_NEW_CONFIRM = "admin:season_new_confirm"
CB_ADMIN_SEASON_BUMP_VERSION = "admin:season_bump"

CB_ADMIN_PROMO = "admin:promo"
CB_ADMIN_PROMO_CREATE = "admin:promo_create"

CB_ADMIN_REFERRAL = "admin:referral"
CB_ADMIN_REFERRAL_CREATE = "admin:referral_create"
CB_ADMIN_REFERRAL_DETAIL_PREFIX = "admin:referral_detail:"

CB_ADMIN_BROADCAST_START = "admin:broadcast"
CB_ADMIN_BROADCAST_CONFIRM = "admin:broadcast_confirm"

CB_ADMIN_MASS_GRANT = "admin:mass_grant"
CB_ADMIN_MASS_GRANT_DUST = "admin:mass_dust"
CB_ADMIN_MASS_GRANT_COINS = "admin:mass_coins"
CB_ADMIN_MASS_GRANT_TICKETS = "admin:mass_tickets"
CB_ADMIN_MASS_GRANT_CONFIRM = "admin:mass_confirm"

CB_ADMIN_DELETE_ACCOUNT_START = "admin:delete_account"
CB_ADMIN_DELETE_ACCOUNT_CONFIRM_PREFIX = "admin:delete_confirm:"

# Управление доп.админами — только для супер-админов (ADMIN_IDS), см. handlers/admin/admin_manage.
CB_ADMIN_MANAGE_ADMINS = "admin:manage_admins"
CB_ADMIN_MANAGE_FIND_PLAYER = "admin:manage_find_player"
CB_ADMIN_TOGGLE_ADMIN_PREFIX = "admin:toggle_admin:"

# Полное удаление БД — только для супер-админов, см. handlers/admin/db_wipe.
CB_ADMIN_WIPE_START = "admin:wipe_start"
CB_ADMIN_WIPE_CONFIRM = "admin:wipe_confirm"

# Ивенты — доступно ЛЮБОМУ админу (не только супер-админу), см. handlers/admin/events.
CB_ADMIN_EVENTS = "admin:events"
CB_ADMIN_EVENT_TOGGLE_PREFIX = "admin:event_toggle:"
