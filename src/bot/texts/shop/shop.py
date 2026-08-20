from __future__ import annotations

SHOP_SCREEN = "🛒 <b>Магазин</b>\n\n✨ <b>Пыль:</b> {dust}\n💎 <b>Коины:</b> {coins}\n\nВыбери раздел:"
BTN_SHOP_DUST = "✨ Магазин пыли"
BTN_SHOP_COINS = "💎 Магазин коинов"

DUST_SHOP_SCREEN = (
    "✨ <b>Магазин пыли</b>\n\n"
    "<b>Пыль:</b> {dust}\n"
    "<b>Курс:</b> 1 тикет = {price} пыли\n\n"
    "Сколько тикетов купить?"
)
BTN_TICKET_PRESET = "{qty} шт."
BTN_BUY_MAX = "🔝 Максимум"
BTN_CUSTOM_QUANTITY = "✏️ Своё число"

CUSTOM_QUANTITY_PROMPT = "Введите количество тикетов (целое число от 1 до {max}).\n\n/cancel — отменить."
CUSTOM_QUANTITY_INVALID = "Нужно целое число от 1 до {max}. Попробуйте ещё раз."
CUSTOM_QUANTITY_CANCELLED = "Покупка отменена."

BUY_TICKETS_RESULT = "✅ Куплено тикетов: <b>{qty}</b> за <b>{cost}</b> пыли."
# Telegram НЕ поддерживает HTML/markdown в popup-алертах (callback.answer(show_alert=True))
# — только в обычных сообщениях чата. Обычные <b> в BUY_TICKETS_RESULT там показались бы
# как есть, буквально "<b>232</b>". Для попапа — версия без разметки.
BUY_TICKETS_RESULT_ALERT = "✅ Куплено тикетов: {qty} за {cost} пыли."
NOT_ENOUGH_DUST = "Не хватает пыли: нужно {needed}."
NOT_ENOUGH_COINS = "Не хватает коинов: нужно {needed}."
BUY_MAX_NOTHING = "Пыли не хватает даже на 1 тикет."

# Магазин коинов — общее
COIN_SHOP_SCREEN = "💎 <b>Магазин коинов</b>\n\n<b>Коины:</b> {coins}\n\nВыбери раздел:"
BTN_SUBSCRIPTION = "⭐ Подписка"
BTN_BATTLE_PASS = "🎫 Battle Pass"
BTN_COIN_TICKETS = "🎫 Тикеты"
BTN_CASINO = "🎰 Казино"
BTN_TICKET_CAP = "📦 Макс хранилище"
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
    "🎫 <b>Тикеты за коины</b>\n\n"
    "<b>Курс:</b> 1 тикет = {price} коинов\n"
    "<b>Коины:</b> {coins}\n\n"
    "Сколько тикетов купить? (1-{max})\n\n"
    "/cancel — отменить."
)
COIN_TICKETS_INVALID = "Нужно целое число от 1 до {max}. Попробуйте ещё раз."
COIN_TICKETS_CONFIRM = "Купить {qty} тикетов за {cost} коинов?"
COIN_TICKETS_BOUGHT = "✅ Куплено тикетов: <b>{qty}</b> за <b>{cost}</b> коинов."

# Магазин: слот капа тикетов (за коины, см. CLAUDE.md, "Магазин: слот капа тикетов") —
# изменено 2026-08-17: раньше продавался за рубли через YooKassa-инвойс, теперь пакет в
# магазине коинов, тем же паттерном "пресеты + своё число -> подтверждение", что и другие
# покупки за коины.
TICKET_CAP_SCREEN = (
    "📦 <b>Макс хранилище</b>\n\n"
    "Каждый слот прибавляет +{bonus} к потолку пассивной регенерации тикетов "
    "(сейчас {natural_cap}).\n\n"
    "<b>Перманентный бонус:</b> +{permanent}\n"
    "<b>Сезонный бонус:</b> +{seasonal}\n"
    "<b>Итоговый кап:</b> {total_cap}"
)
BTN_TICKET_CAP_SEASONAL = "🗓 Сезонный слот — {price} коинов/шт"
BTN_TICKET_CAP_PERMANENT = "♾ Перманентный слот — {price} коинов/шт"
TICKET_CAP_NO_SEASON = "Сейчас нет активного сезона — сезонный слот покупать не за чем."

TICKET_CAP_QUANTITY_SCREEN_SEASONAL = "🗓 <b>Сезонный слот капа</b>\n\n<b>Цена:</b> {price} коинов/шт\n<b>Коины:</b> {coins}\n\nСколько слотов купить?"
TICKET_CAP_QUANTITY_SCREEN_PERMANENT = "♾ <b>Перманентный слот капа</b>\n\n<b>Цена:</b> {price} коинов/шт\n<b>Коины:</b> {coins}\n\nСколько слотов купить?"
TICKET_CAP_CUSTOM_PROMPT = "Введите количество слотов (целое число от 1 до {max}).\n\n/cancel — отменить."
TICKET_CAP_CUSTOM_INVALID = "Нужно целое число от 1 до {max}. Попробуйте ещё раз."
TICKET_CAP_ASK_SEASONAL = "Купить {qty} сезонных слотов за {cost} коинов?"
TICKET_CAP_ASK_PERMANENT = "Купить {qty} перманентных слотов за {cost} коинов?"
TICKET_CAP_BOUGHT = "✅ Куплено слотов: <b>{qty}</b> за <b>{cost}</b> коинов. Новый бонус: +{bonus}."
