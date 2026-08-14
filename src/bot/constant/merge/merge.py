"""callback_data-префиксы и lock-ключ домена "Слияния" — отдельный от "Коллекции" флоу
(тир-пикер -> список карт, доступных для слияния -> целевая звезда, см. CLAUDE.md).
Карта в списке/действии адресуется натуральным ключом (card_id, stars), а не индексом в
списке — устойчиво к тому, что состав списка меняется после самого слияния."""

from __future__ import annotations

CB_MERGE_OPEN = "merge:open"
CB_MERGE_ALL_TO_MAX = "merge:all_to_max"
CB_MERGE_TIER_PREFIX = "merge:tier:"
CB_MERGE_EVENTS = "merge:events"
CB_MERGE_TIER_PAGE_PREFIX = "merge:tierpage:"
CB_MERGE_STACK_PREFIX = "merge:stack:"
CB_MERGE_ACTION_PREFIX = "merge:do:"

LOCK_ACTION_MERGE = "merge"

TRANSACTION_REASON_MERGE = "merge"
