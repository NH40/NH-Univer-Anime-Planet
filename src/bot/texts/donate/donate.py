from __future__ import annotations

DONATE_SCREEN = (
    "💎 <b>Донат</b>\n\n"
    "Пополнение баланса коинов картой или по СБП (1₽ = 1 коин).\n"
    "Текущий баланс: <b>{coins}</b> коинов."
)
BTN_DONATE_CUSTOM = "✏️ Своя сумма"
DONATE_CUSTOM_PROMPT = "Введите сумму пополнения в рублях ({min}-{max} ₽)."
DONATE_CUSTOM_INVALID = "Сумма должна быть целым числом от {min} до {max} ₽."
DONATE_CANCELLED = "Отменено."
DONATE_NOT_CONFIGURED = "Донат временно недоступен."

DONATE_INVOICE_TITLE = "Пополнение коинов"
DONATE_INVOICE_DESCRIPTION = "{amount} коинов на баланс Universe Anime Planet."
DONATE_INVOICE_LABEL = "{amount} коинов"

DONATE_SUCCESS = "✅ Оплата прошла! Начислено {coins} коинов."

# Выбор способа и оплата по СБП (2026-10-30).
DONATE_METHOD_SCREEN = (
    "💎 <b>Пополнение коинов</b>\n\n"
    "💰 Сумма: <b>{amount} ₽</b> → {amount} коинов\n\n"
    "Выберите способ оплаты 👇"
)
BTN_PAY_SBP = "⚡ СБП"
BTN_PAY_CARD = "💳 Картой (ЮKassa)"
BTN_SBP_PAY = "💳 Оплатить {amount} ₽"
BTN_SBP_CHECK = "🔄 Я оплатил"
BTN_DONATE_BACK = "◀️ Назад"
DONATE_SBP_SCREEN = (
    "⚡ <b>Оплата по СБП</b>\n\n"
    "<blockquote>⏳ Оплатите в течение {minutes} мин — откроется приложение банка или QR-код.</blockquote>\n\n"
    "💰 Сумма: <b>{amount} ₽</b>\n\n"
    "Коины придут сами сразу после оплаты. Если не пришли — нажмите «Я оплатил».\n"
    "Нажмите кнопку оплаты ниже 👇"
)
DONATE_SBP_PAID_SCREEN = "✅ <b>Оплачено по СБП</b>\n\n{amount} ₽ → начислено {coins} коинов."
DONATE_SBP_CANCELED_SCREEN = "❌ Платёж по СБП отменён или истёк. Создайте новый — «◀️ Назад»."
DONATE_SBP_FAILED = "Не удалось создать платёж по СБП. Попробуйте позже или оплатите картой."
DONATE_SBP_WAITING = "Оплата ещё не поступила. Если вы уже оплатили — подождите минуту и нажмите снова."
DONATE_SBP_ALREADY = "Этот платёж уже зачислен ✅"
DONATE_SBP_DONE_ALERT = "✅ Оплата получена!"
DONATE_SBP_BUSY = "Обрабатываю…"
