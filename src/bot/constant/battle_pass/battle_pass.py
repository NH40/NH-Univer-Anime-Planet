from __future__ import annotations

TRANSACTION_REASON_PASS_FREE = "battle_pass_free_reward"
TRANSACTION_REASON_PASS_PREMIUM = "battle_pass_premium_reward"

LOCK_ACTION_CLAIM_PASS_FREE = "claim_battle_pass_free"
LOCK_ACTION_CLAIM_PASS_PREMIUM = "claim_battle_pass_premium"

CB_BATTLE_PASS_OPEN = "battle_pass:open"
CB_BATTLE_PASS_CLAIM_FREE = "battle_pass:claim_free"
CB_BATTLE_PASS_CLAIM_PREMIUM = "battle_pass:claim_premium"

# Лента уровней (📜 Все уровни) — page кодируется суффиксом в callback_data.
CB_BATTLE_PASS_LEVELS_PAGE_PREFIX = "battle_pass:levels:"
CB_BATTLE_PASS_LEVELS_CLAIM_FREE_PREFIX = "battle_pass:levels_claim_free:"
CB_BATTLE_PASS_LEVELS_CLAIM_PREMIUM_PREFIX = "battle_pass:levels_claim_premium:"
