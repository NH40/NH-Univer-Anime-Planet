from __future__ import annotations

CB_CASINO_OPEN = "casino:open"
CB_CASINO_GAME_PREFIX = "casino:game:"
CB_CASINO_ROLL_PREFIX = "casino:roll:"
# Масс-крутка — только для кубика (так решил пользователь), но callback параметризован
# игрой на случай, если это когда-нибудь расширят.
CB_CASINO_MASS_PREFIX = "casino:mass:"
CB_CASINO_MASS_CONFIRM = "casino:mass:confirm"

LOCK_ACTION_CASINO_ROLL = "casino_roll"
LOCK_ACTION_CASINO_MASS_ROLL = "casino_mass_roll"

TRANSACTION_REASON_CASINO_ROLL = "casino_roll"
TRANSACTION_REASON_CASINO_MASS_ROLL = "casino_mass_roll"
