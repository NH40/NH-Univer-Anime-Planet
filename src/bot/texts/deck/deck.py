from __future__ import annotations

BTN_ROLL_1 = "🎴 Крутить 1"
BTN_ROLL_10 = "🎰 Крутить 10"
BTN_COLLECTION = "📚 Коллекция"
BTN_DISENCHANT = "💨 Распылить"
BTN_MERGE = "🔗 Слияние"
BTN_CHANCES = "🎲 Шансы"

DECK_SCREEN = "🃏 <b>Колода</b>\n\nВселенная: {universe}\nТикеты: <b>{tickets}/{cap}</b>\nПыль: <b>{dust}</b>"
NO_UNIVERSE_SELECTED = "Сначала выбери вселенную командой /settings."
UNIVERSE_NOT_READY = (
    "Вселенная «{universe}» пока не полностью заполнена картами (нет карт в тире "
    "{tiers} UBP) — крутка временно недоступна, загляните позже."
)
NOT_ENOUGH_TICKETS = (
    "Не хватает тикетов: нужно {needed}. Тикеты копятся по 1 за 2 часа (бесплатный "
    "максимум — {cap}), докупить сверх можно в магазине или промокодом."
)
NO_ACTIVE_SEASON = "Сейчас нет активного сезона — крутка временно недоступна."

CARD_CAPTION = (
    "🆔 <b>ID:</b> {external_id}\n"
    "🎴 <b>Персонаж:</b> {name}\n"
    "🌌 <b>Вселенная:</b> {universe}\n\n"
    "📖 {description}\n\n"
    "📦 <b>Количество:</b> {quantity}\n"
    "💠 <b>Очки:</b> {ubp}\n"
    "🌟 <b>Звёзды:</b> {stars}"
)
NO_DESCRIPTION = "—"

ROLL_TEN_RESULT_HEADER = "🎰 <b>Результаты крутки x10:</b>\n"
ROLL_TEN_LINE = "{i}. {name} — {ubp} UBP\n"

CHANCES_HEADER = "🎲 <b>Шансы</b> — {universe}\n\n"
CHANCES_TIER_LINE = "\n<b>{ubp} UBP — {chance}%</b>\n"
CHANCES_CARD_LINE = "  id:{external_id} — {name}\n"
CHANCES_UNDISCOVERED = "???"
