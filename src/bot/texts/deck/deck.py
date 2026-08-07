from __future__ import annotations

BTN_ROLL_1 = "🎴 Крутить"
BTN_ROLL_AGAIN = "🎴 Крутить ещё"
BTN_COLLECTION = "📚 Коллекция"
BTN_DISENCHANT = "✨ Распылить"
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
    "🌌 <b>Вселенная:</b> {universe}\n"
    "💠 <b>Очки:</b> {ubp}\n\n"
    "📖 <b>Описание:</b>\n{description}\n\n"
    "📦 <b>Количество:</b> {quantity}\n"
    "{tier_emoji} <b>Ранг:</b> {tier_name}\n"
    "🌟 <b>Звёзды:</b> {stars}"
)
NO_DESCRIPTION = "—"

# Названия и цветные кружки тиров (1000-6000 UBP) для экрана "Шансы" — чисто
# презентационная лесенка редкости, порядок значения не меняет (см. config/game:
# TIER_CHANCE_PERCENT — та же связка UBP->тир, но с числами шанса, не именами).
TIER_NAMES = {
    1000: "Обычный",
    2000: "Необычный",
    3000: "Редкий",
    4000: "Эпический",
    5000: "Легендарный",
    6000: "Мифический",
}
TIER_EMOJI = {
    1000: "⚪",
    2000: "🟢",
    3000: "🔵",
    4000: "🟣",
    5000: "🟠",
    6000: "🔴",
}

CHANCES_HEADER = "🎲 <b>Шансы выпадения</b> — {universe}\n\nВыбери тир, чтобы увидеть персонажей:"
BTN_CHANCES_TIER = "{emoji} {name} — {chance}% ({count})"

CHANCES_TIER_HEADER = "{emoji} <b>{name}</b> — {chance}%\n\nВсего персонажей: {count}\n\n"
CHANCES_CARD_LINE = "{i}. {name}\n"
CHANCES_UNDISCOVERED = "???"
BTN_BACK_CHANCES = "◀️ К шансам"
