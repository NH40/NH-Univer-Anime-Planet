from __future__ import annotations

CB_SHOP_OPEN = "shop:open"
CB_SHOP_DUST = "shop:dust"
CB_SHOP_COINS = "shop:coins"
CB_SHOP_BUY_TICKETS_PREFIX = "shop:buy_tickets:"
CB_SHOP_BUY_TICKETS_CUSTOM = "shop:buy_tickets_custom"
CB_SHOP_BUY_TICKETS_MAX = "shop:buy_tickets_max"

# Магазин коинов: подписка / Battle Pass / тикеты за коины
CB_COINSHOP_SUBSCRIPTION = "cshop:sub"
CB_COINSHOP_SUBSCRIPTION_CONFIRM = "cshop:sub:confirm"
CB_COINSHOP_BATTLE_PASS = "cshop:bp"
CB_COINSHOP_BATTLE_PASS_CONFIRM = "cshop:bp:confirm"
CB_COINSHOP_TICKETS = "cshop:tickets"
CB_COINSHOP_TICKETS_CONFIRM = "cshop:tickets:confirm"
# Общая кнопка отмены для флоу "ввели число -> подтвердите" (тикеты за коины, масс-крутка
# казино) — один и тот же смысл ("отменено"), не нужно два разных callback'а под него.
CB_COINSHOP_CANCEL = "cshop:cancel"

LOCK_ACTION_BUY_TICKETS = "buy_tickets"
LOCK_ACTION_BUY_SUBSCRIPTION = "buy_subscription"
LOCK_ACTION_BUY_BATTLE_PASS = "buy_battle_pass"
LOCK_ACTION_BUY_COIN_TICKETS = "buy_coin_tickets"

TRANSACTION_REASON_SHOP_TICKET = "shop_ticket"
TRANSACTION_REASON_SUBSCRIPTION = "subscription"
TRANSACTION_REASON_BATTLE_PASS = "battle_pass"
TRANSACTION_REASON_SHOP_COIN_TICKET = "shop_coin_ticket"
