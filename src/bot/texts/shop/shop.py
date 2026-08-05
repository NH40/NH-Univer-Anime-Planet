from __future__ import annotations

SHOP_SCREEN = "🛒 <b>Магазин</b>\n\n💨 <b>Пыль:</b> {dust}\n🪙 <b>Коины:</b> {coins}\n\nВыбери раздел:"
BTN_SHOP_DUST = "💨 Магазин пыли"
BTN_SHOP_COINS = "🪙 Магазин коинов"

DUST_SHOP_SCREEN = (
    "💨 <b>Магазин пыли</b>\n\n"
    "<b>Пыль:</b> {dust}\n"
    "<b>Курс:</b> 1 тикет = {price} пыли\n\n"
    "Сколько тикетов купить?"
)
BTN_TICKET_PRESET = "{qty} шт."
BTN_CUSTOM_QUANTITY = "✏️ Своё число"

CUSTOM_QUANTITY_PROMPT = "Введите количество тикетов (целое число от 1 до {max}). /cancel — отменить."
CUSTOM_QUANTITY_INVALID = "Нужно целое число от 1 до {max}. Попробуйте ещё раз."
CUSTOM_QUANTITY_CANCELLED = "Покупка отменена."

BUY_TICKETS_RESULT = "✅ Куплено тикетов: <b>{qty}</b> за <b>{cost}</b> пыли."
NOT_ENOUGH_DUST = "Не хватает пыли: нужно {needed}."
NOT_ENOUGH_COINS = "Не хватает коинов: нужно {needed}."

# Магазин коинов — общее
COIN_SHOP_SCREEN = "🪙 <b>Магазин коинов</b>\n\n<b>Коины:</b> {coins}\n\nВыбери раздел:"
BTN_SUBSCRIPTION = "⭐ Подписка"
BTN_BATTLE_PASS = "🎫 Battle Pass"
BTN_COIN_TICKETS = "🎟 Тикеты"
BTN_CASINO = "🎰 Казино"
BTN_CONFIRM = "✅ Подтвердить"
BTN_CANCEL = "❌ Отменить"
CANCELLED = "Отменено."

# Подписка
SUBSCRIPTION_SCREEN = (
    "⭐ <b>Подписка</b>\n\n"
    "<b>Цена:</b> {price} коинов / {days} дней\n"
    "<i>Покупки складываются — купил ещё раз, срок увеличивается.</i>\n\n"
    "Пока активна:\n"
    "⚡ Реген тикетов вдвое быстрее — 1 тикет/час вместо 1/2 часа\n"
    "🎁 +5 тикетов каждые 24 часа\n\n"
    "<b>Статус:</b> {status}\n"
    "<b>Коины:</b> {coins}"
)
SUBSCRIPTION_STATUS_ACTIVE = "✅ активна до {until}"
SUBSCRIPTION_STATUS_NONE = "не активна"
BTN_BUY_SUBSCRIPTION = "Купить за {price} коинов"
SUBSCRIPTION_BOUGHT = "✅ Подписка активна до {until}."

# Battle Pass (только покупка премиум-доступа) — разовая покупка на весь текущий сезон,
# не подписка на дни (см. CLAUDE.md, "Сезонный пасс").
BATTLE_PASS_SCREEN = (
    "🎫 <b>Battle Pass</b>\n\n"
    "<b>Цена:</b> {price} коинов — открывает премиум-ветку до конца текущего сезона\n\n"
    "<b>Статус:</b> {status}\n"
    "<b>Коины:</b> {coins}"
)
BATTLE_PASS_STATUS_ACTIVE = "✅ премиум открыт в этом сезоне"
BATTLE_PASS_STATUS_NONE = "премиум не открыт"
BTN_BUY_BATTLE_PASS = "Купить за {price} коинов"
BATTLE_PASS_BOUGHT = "✅ Премиум-ветка Battle Pass открыта до конца сезона!"
BATTLE_PASS_ALREADY_PREMIUM = "Премиум уже открыт в этом сезоне."
BATTLE_PASS_NO_SEASON = "Сейчас нет активного сезона."

# Тикеты за коины
COIN_TICKETS_SCREEN = (
    "🎟 <b>Тикеты за коины</b>\n\n"
    "<b>Курс:</b> 1 тикет = {price} коинов\n"
    "<b>Коины:</b> {coins}\n\n"
    "Введите количество тикетов, которое хотите купить (1-{max}). /cancel — отменить."
)
COIN_TICKETS_INVALID = "Нужно целое число от 1 до {max}. Попробуйте ещё раз."
COIN_TICKETS_CONFIRM = "Купить {qty} тикетов за {cost} коинов?"
COIN_TICKETS_BOUGHT = "✅ Куплено тикетов: <b>{qty}</b> за <b>{cost}</b> коинов."
