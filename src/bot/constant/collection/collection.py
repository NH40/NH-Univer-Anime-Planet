"""callback_data-префиксы домена "Коллекция" (тир-пикер, навигация по стопкам карт) —
единая точка правды для клавиатур и хендлеров. Коллекция чисто просмотровая — слияние и
распыление живут в отдельных доменах constant/merge и constant/dust (см. CLAUDE.md)."""

from __future__ import annotations

CB_COLL_TIER_PREFIX = "coll:tier:"
CB_COLL_EVENTS = "coll:events"
CB_COLL_NAV_PREFIX = "coll:nav:"
