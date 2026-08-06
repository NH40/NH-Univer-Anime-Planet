"""callback_data-префиксы и lock-ключи домена "Коллекция" (тир-пикер, навигация по
стопкам, распыление, слияние) — единая точка правды для клавиатур и хендлеров."""

from __future__ import annotations

CB_COLL_TIER_PREFIX = "coll:tier:"
CB_COLL_EVENTS = "coll:events"
CB_COLL_NAV_PREFIX = "coll:nav:"
CB_COLL_DUST1_PREFIX = "coll:dust1:"
CB_COLL_DUSTALL_PREFIX = "coll:dustall:"
CB_COLL_MERGE_PREFIX = "coll:merge:"

LOCK_ACTION_DUST = "dust"
LOCK_ACTION_MERGE = "merge"
