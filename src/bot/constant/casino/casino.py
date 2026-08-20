from __future__ import annotations

CB_CASINO_OPEN = "casino:open"
CB_CASINO_GAME_PREFIX = "casino:game:"
CB_CASINO_ROLL_PREFIX = "casino:roll:"
# Масс-крутка — только для кубика (так решил пользователь), но callback параметризован
# игрой на случай, если это когда-нибудь расширят.
CB_CASINO_MASS_PREFIX = "casino:mass:"
# НЕ "casino:mass:confirm" — тот startswith(CB_CASINO_MASS_PREFIX), поэтому cb_mass_roll_start
# (зарегистрирован раньше, ловит по префиксу) перехватывал бы клик "Подтвердить" первым,
# приняв "confirm" за game-код, и молча его отбрасывал — кнопка подтверждения ничего не
# делала (баг, найден 2026-08-17). Разный корень строки исключает коллизию структурно.
CB_CASINO_MASS_CONFIRM = "casino:massconfirm"

LOCK_ACTION_CASINO_ROLL = "casino_roll"
LOCK_ACTION_CASINO_MASS_ROLL = "casino_mass_roll"

TRANSACTION_REASON_CASINO_ROLL = "casino_roll"
TRANSACTION_REASON_CASINO_MASS_ROLL = "casino_mass_roll"
