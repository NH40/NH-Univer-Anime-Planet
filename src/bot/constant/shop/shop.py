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

# Паки — отдельная категория в магазине коинов (см. CLAUDE.md), сейчас единственный пак —
# макс хранилище, задел на будущие паки без переделки структуры меню.
CB_COINSHOP_PACKS = "cshop:packs"

# Слот капа тикетов (см. CLAUDE.md, "Магазин: слот капа тикетов") — за коины, тот же
# паттерн покупки за коины, что тикеты/подписка/Battle Pass (изменено 2026-08-17, раньше
# было за рубли через YooKassa-инвойс). SEASONAL/PERMANENT открывают экран выбора
# количества (пресеты + своё число), не покупают напрямую.
CB_COINSHOP_TICKET_CAP = "cshop:ticket_cap"
CB_COINSHOP_TICKET_CAP_SEASONAL = "cshop:ticket_cap:seasonal"
CB_COINSHOP_TICKET_CAP_PERMANENT = "cshop:ticket_cap:permanent"
# +f"{kind}:{qty}", kind — "seasonal"/"permanent". ASK показывает подтверждение (тот же
# принцип "тап не исполняет действие сразу", что у распыления, см. CLAUDE.md), BUY —
# реальная покупка, на неё же ссылается кнопка "Подтвердить" экрана ASK.
CB_COINSHOP_TICKET_CAP_ASK_PREFIX = "cshop:ticket_cap:ask:"
CB_COINSHOP_TICKET_CAP_BUY_PREFIX = "cshop:ticket_cap:buy:"
# +kind
CB_COINSHOP_TICKET_CAP_CUSTOM_PREFIX = "cshop:ticket_cap:custom:"

# `kind` для покупки/выдачи слота капа (сравнивается в services/shop, handlers/shop,
# handlers/admin — константа, а не строковый литерал, см. CLAUDE.md).
TICKET_CAP_KIND_SEASONAL = "seasonal"
TICKET_CAP_KIND_PERMANENT = "permanent"

LOCK_ACTION_BUY_TICKETS = "buy_tickets"
LOCK_ACTION_BUY_SUBSCRIPTION = "buy_subscription"
LOCK_ACTION_BUY_BATTLE_PASS = "buy_battle_pass"
LOCK_ACTION_BUY_COIN_TICKETS = "buy_coin_tickets"
LOCK_ACTION_BUY_TICKET_CAP = "buy_ticket_cap"

TRANSACTION_REASON_SHOP_TICKET = "shop_ticket"
TRANSACTION_REASON_SUBSCRIPTION = "subscription"
TRANSACTION_REASON_BATTLE_PASS = "battle_pass"
TRANSACTION_REASON_SHOP_COIN_TICKET = "shop_coin_ticket"
TRANSACTION_REASON_TICKET_CAP_SEASONAL = "ticket_cap_seasonal"
TRANSACTION_REASON_TICKET_CAP_PERMANENT = "ticket_cap_permanent"
