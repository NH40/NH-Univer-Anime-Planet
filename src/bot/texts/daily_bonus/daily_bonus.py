from __future__ import annotations

DAILY_BONUS_SCREEN = (
    "🎁 <b>Ежедневный бонус</b>\n\n"
    "{cells}\n\n"
    "{status_line}\n\n"
    "<b>Награда за день {day}:</b> {dust} пыли, {tickets} тикетов"
)
# ✅ — уже забранный день серии, 🎁 — сегодняшний день (доступен к сбору), ▫️ — ещё впереди.
CELL_DONE = "✅"
CELL_READY = "🎁"
CELL_FUTURE = "▫️"

STATUS_READY = "Готово к получению!"
STATUS_READY_RESET = "⚠️ Серия прервана — сегодняшний сбор начнёт её заново с 1 дня."
STATUS_COUNTDOWN = "⏳ Следующий бонус через {mm:02d}:{ss:02d}"

BTN_CLAIM = "🎁 Забрать"

CLAIM_DONE = "✅ День {day}: +{dust} пыли, +{tickets} тикетов!"
CLAIM_ALREADY = "Бонус на сегодня уже получен."
