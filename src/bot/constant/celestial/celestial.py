from __future__ import annotations

# --- Небесные карты (см. CLAUDE.md, "Небесные карты") ---
CB_CELESTIAL_OPEN = "celestial:open"
CB_CELESTIAL_CARD_PREFIX = "celestial:card:"
CB_CELESTIAL_ACCEPT_PREFIX = "celestial:accept:"
CB_CELESTIAL_DECLINE_PREFIX = "celestial:decline:"
# Отдельный подтверждающий шаг перед реальным отказом (см. CLAUDE.md, правило про
# необратимые действия рядом с обычными кнопками) — тот же паттерн "_ASK_PREFIX", что у
# точечного распыления.
CB_CELESTIAL_DECLINE_CONFIRM_PREFIX = "celestial:decline_confirm:"
CB_CELESTIAL_THROW_PREFIX = "celestial:throw:"

# Идемпотентность (правило 2) — один лок на связку "игрок + это конкретное действие с
# конкретной картой" (card_id дописывается в хендлере к базовому имени, тот же паттерн,
# что LOCK_ACTION_DUST + card_id в других домена — см. cache.keys.action_lock).
LOCK_ACTION_CELESTIAL_ACCEPT = "celestial_accept"
LOCK_ACTION_CELESTIAL_DECLINE = "celestial_decline"
LOCK_ACTION_CELESTIAL_THROW = "celestial_throw"

# reason в transactions — три разных источника UBP от небесных/божественных карт (см.
# CLAUDE.md): дроп небесной (и владельцу, и претенденту — оба реально "выбили" карту своей
# круткой), божественная за полный ростер вселенной, божественная за все небесные разом.
TRANSACTION_REASON_CELESTIAL_DROP = "celestial_drop"
TRANSACTION_REASON_DIVINE_UNIVERSE = "divine_universe"
TRANSACTION_REASON_DIVINE_GLOBAL = "divine_global"
TRANSACTION_REASON_DIVINE_PSEUDO = "divine_pseudo"
