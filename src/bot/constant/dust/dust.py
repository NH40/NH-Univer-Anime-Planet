"""callback_data-префиксы и lock-ключ домена "Распыление" — отдельный от "Коллекции" флоу:
экран режимов (Выбор / Распылить всё / Все повторки) -> для "Выбор" тир-пикер -> список
карт тира -> точечное действие. Карта адресуется натуральным ключом (card_id, stars), не
индексом в списке (см. constant/merge — тот же принцип)."""

from __future__ import annotations

CB_DUST_OPEN = "dust:open"
CB_DUST_SELECT = "dust:select"
CB_DUST_MODE_ALL = "dust:mode_all"
CB_DUST_MODE_DUPES = "dust:mode_dupes"
CB_DUST_MODE_ALL_CONFIRM = "dust:mode_all_confirm"
CB_DUST_MODE_DUPES_CONFIRM = "dust:mode_dupes_confirm"
CB_DUST_MODE_CANCEL = "dust:mode_cancel"
CB_DUST_TIER_PREFIX = "dust:tier:"
CB_DUST_EVENTS = "dust:events"
CB_DUST_TIER_PAGE_PREFIX = "dust:tierpage:"
CB_DUST_STACK_PREFIX = "dust:stack:"
CB_DUST_AMOUNT_PREFIX = "dust:amount:"
CB_DUST_CUSTOM_PREFIX = "dust:custom:"
CB_DUST_DUPES_PREFIX = "dust:dupes:"
CB_DUST_ALL_PREFIX = "dust:all:"
# "_ask" — промежуточный экран подтверждения перед точечным распылением (подтверждено
# пользователем 2026-08-14: одно случайное нажатие рядом со "Слиянием" не должно уничтожать
# карты без единого лишнего клика) — сами _PREFIX выше остаются финальными исполнителями,
# на них ведёт кнопка "Да" с экрана подтверждения.
CB_DUST_AMOUNT_ASK_PREFIX = "dust:amount_ask:"
CB_DUST_DUPES_ASK_PREFIX = "dust:dupes_ask:"
CB_DUST_ALL_ASK_PREFIX = "dust:all_ask:"

LOCK_ACTION_DUST = "dust"

TRANSACTION_REASON_DUST = "dust"
