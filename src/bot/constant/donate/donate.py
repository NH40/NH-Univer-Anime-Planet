from __future__ import annotations

TRANSACTION_REASON_DONATE = "donate_yookassa"

CB_DONATE_OPEN = "donate:open"
CB_DONATE_PRESET_PREFIX = "donate:preset:"
CB_DONATE_CUSTOM = "donate:custom"
# Выбор способа оплаты после суммы (2026-10-30): карта (форма Telegram) или СБП.
CB_DONATE_CARD_PREFIX = "donate:card:"  # + рубли
CB_DONATE_SBP_PREFIX = "donate:sbp:"  # + рубли
CB_DONATE_SBP_CHECK_PREFIX = "donate:sbpchk:"  # + id строки sbp_payments
LOCK_ACTION_DONATE_SBP = "donate_sbp"

# Статусы счёта СБП (`sbp_payments.status`).
SBP_STATUS_PENDING = "pending"
SBP_STATUS_SUCCEEDED = "succeeded"
SBP_STATUS_CANCELED = "canceled"
SBP_STATUS_EXPIRED = "expired"  # бот перестал проверять сам; вебхук/«Я оплатил» всё равно зачислят
# Метка бота в metadata платежа ЮKassa: если оба бота на одном магазине, вебхук одного
# пропускает чужие платежи (их подберёт фоновая проверка другого бота).
SBP_METADATA_BOT = "uap"
