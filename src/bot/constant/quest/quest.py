from __future__ import annotations

TRANSACTION_REASON_QUEST = "daily_quest"

CB_QUEST_CLAIM_PREFIX = "quest:claim:"
CB_QUEST_CLAIM_ALL = "quest:claim_all"
CB_QUEST_REROLL_ALL = "quest:reroll_all"
CB_QUEST_REROLL_PREFIX = "quest:reroll:"

# Redis-лок на время обработки claim/reroll (SET NX PX, см. CLAUDE.md, правило 2) — ключуется
# по user_id+action, не по конкретному слоту: двойной клик по ЛЮБОЙ кнопке заданий подряд
# должен игнорироваться, не только по одной и той же.
LOCK_ACTION_QUEST_CLAIM = "quest_claim"
LOCK_ACTION_QUEST_REROLL = "quest_reroll"
