from __future__ import annotations

DUST_OPEN_HEADER = "✨ <b>Распыление</b>\n\nВыбери режим:"
BTN_MODE_SELECT = "🔍 Выбор"
BTN_MODE_ALL = "✨ Распылить всё"
BTN_MODE_DUPES = "♻️ Все повторки"

CONFIRM_ALL = "⚠️ Точно распылить ВСЮ коллекцию? Это необратимо."
CONFIRM_DUPES = "⚠️ Точно распылить все повторки, оставив по 1 копии каждой карты?"
BTN_CONFIRM = "✅ Подтвердить"
BTN_CANCEL = "❌ Отмена"

BULK_RESULT = "✨ Распылено! Получено +{reward} пыли."
BULK_NOTHING = "Нечего распылять — коллекция уже пуста от дубликатов."

DUST_TIER_PICKER_HEADER = "✨ <b>Распыление</b> — {universe}\n\nВыбери тир:"
DUST_STACK_LIST_HEADER = "✨ <b>Распыление</b>\n\nВыбери карту:"
TIER_BUTTON = "{ubp} UBP"
BTN_EVENTS_TIER = "🎉 Ивенты"
EMPTY_TIER = "В этом тире нет карт."

STACK_BUTTON = "{name} {stars} ({quantity} шт.)"
CARD_ACTION_HEADER = "✨ <b>{name}</b> {stars}\nКопий: <b>{quantity}</b>\n\nСколько распылить?"

BTN_AMOUNT = "Распылить {amount}"
BTN_CUSTOM = "✏️ Своё число"
BTN_DUPES = "♻️ Все дубликаты"
BTN_ALL = "✨ Всё"
BTN_PREV_PAGE = "« Назад"
BTN_NEXT_PAGE = "Вперёд »"
BTN_BACK_TIERS = "◀️ К тирам"
BTN_BACK_STACKS = "◀️ Назад"

DUST_RESULT = "✨ Распылено: {count} шт. → +{reward} пыли."
DUST_NOTHING = "Нечего распылять."
DUST_NOT_ENOUGH = "Не хватает копий — нужно {needed}."

# Подтверждение перед точечным распылением (подтверждено пользователем 2026-08-14 —
# случайный тап рядом со "Слиянием" не должен уничтожать карты без единого лишнего клика).
CONFIRM_AMOUNT = "⚠️ Распылить {amount} шт. «{name}» {stars}? Действие необратимо."
CONFIRM_DUPES_ONE = "⚠️ Распылить все дубликаты «{name}» {stars}, оставив 1 копию? Действие необратимо."
CONFIRM_ALL_ONE = "⚠️ Распылить ВСЕ «{name}» {stars} ({quantity} шт.)? Действие необратимо."

CUSTOM_AMOUNT_PROMPT = "Введи количество карт для распыления (целое число от 1 до {max}).\n\n/cancel — отменить."
CUSTOM_AMOUNT_INVALID = "Некорректное число. Введи целое число от 1 до {max}."
CUSTOM_AMOUNT_CANCELLED = "Отменено."
