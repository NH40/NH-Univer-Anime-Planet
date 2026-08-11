from __future__ import annotations

TRANSACTION_REASON_PASS_FREE = "battle_pass_free_reward"
TRANSACTION_REASON_PASS_PREMIUM = "battle_pass_premium_reward"

# Значение колонки battle_pass_claims.track — сравнивается (services/battle_pass, track:
# Literal["free", "premium"] параметризует общие claim_level/claim_all вместо дублирования
# каждой функции под ветку, см. CLAUDE.md).
TRACK_FREE = "free"
TRACK_PREMIUM = "premium"

LOCK_ACTION_CLAIM_PASS_FREE = "claim_battle_pass_free"
LOCK_ACTION_CLAIM_PASS_PREMIUM = "claim_battle_pass_premium"

CB_BATTLE_PASS_OPEN = "battle_pass:open"

# Лента уровней — page кодируется суффиксом в callback_data. Тап по ОДНОЙ ячейке (см.
# CLAUDE.md, "клейм произвольной ячейки") — level кодируется суффиксом; "Забрать всё" по
# ветке — отдельная кнопка без суффикса.
CB_BATTLE_PASS_LEVELS_PAGE_PREFIX = "battle_pass:levels:"
CB_BATTLE_PASS_LEVELS_CLAIM_FREE_PREFIX = "battle_pass:levels_claim_free:"
CB_BATTLE_PASS_LEVELS_CLAIM_PREMIUM_PREFIX = "battle_pass:levels_claim_premium:"
CB_BATTLE_PASS_CLAIM_ALL_FREE = "battle_pass:claim_all_free"
CB_BATTLE_PASS_CLAIM_ALL_PREMIUM = "battle_pass:claim_all_premium"
