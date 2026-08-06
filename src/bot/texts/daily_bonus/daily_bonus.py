from __future__ import annotations

DAILY_BONUS_SCREEN = (
    "🎁 <b>Ежедневный бонус</b>\n\n"
    "{cells}\n\n"
    "{status_line}\n\n"
    "<b>Награды по дням серии:</b>\n"
    "{rewards_table}"
)
# ✅ — уже забранный день серии, 🎁 — сегодняшний день (доступен к сбору), ▫️ — ещё впереди.
CELL_DONE = "✅"
CELL_READY = "🎁"
CELL_FUTURE = "▫️"

# {marker} — "▶️ " на текущем/следующем дне серии, иначе пусто; {tickets_part} — ", N 🎫",
# если на этот день положены тикеты, иначе пусто (см. handlers/daily_bonus._rewards_table).
REWARD_LINE = "{marker}{day}. {dust} пыли{tickets_part}\n"
REWARD_TICKETS_PART = ", {tickets} 🎫"
REWARD_NEXT_MARKER = "▶️ "

STATUS_READY = "Готово к получению!"
STATUS_READY_RESET = "⚠️ Серия прервана — сегодняшний сбор начнёт её заново с 1 дня."
STATUS_COUNTDOWN = "⏳ Следующий бонус через {time}"

BTN_CLAIM = "🎁 Забрать"

CLAIM_DONE = "✅ День {day}: +{dust} пыли, +{tickets} тикетов!"
CLAIM_ALREADY = "Бонус на сегодня уже получен."
