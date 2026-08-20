from __future__ import annotations

CASINO_SCREEN = "🎰 <b>Казино</b>\n\nКоины: {coins}\n\nВыбери игру:"

# Отображаемые названия игр — ключ совпадает с ключом в config.game.CASINO_EMOJI.
GAME_NAMES: dict[str, str] = {
    "dice": "Кубик",
    "darts": "Дартс",
    "football": "Футбол",
    "basketball": "Баскетбол",
}

GAME_SCREEN = (
    "{emoji} <b>{name}</b>\n\n"
    "Цена: {price} коинов за бросок. Выпавшее число = столько тикетов.\n\n"
    "Коины: {coins}"
)
BTN_ROLL = "Крутить за {price} коинов"
BTN_MASS_ROLL = "🔁 Масс-крутка"

ROLL_RESULT = "{emoji} Выпало: {value}! Получено тикетов: {value}."

MASS_ROLL_PROMPT = "Сколько раз крутить кубик? (1-{max})"
MASS_ROLL_INVALID = "Нужно целое число от 1 до {max}. Попробуйте ещё раз."
MASS_ROLL_CONFIRM = "Крутить {qty} раз за {cost} коинов?"
MASS_ROLL_RESULT = "🎲 Результаты: {values}\nВсего тикетов: {total} (потрачено {cost} коинов)."
