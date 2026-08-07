from __future__ import annotations

PASS_SCREEN = (
    "🎫 <b>Сезонный пасс</b>\n\n"
    "<b>Уровень:</b> {level}\n"
    "{bar}{progress}\n\n"
    "🎁 <b>Бесплатная ветка</b>\n"
    "{free_line}\n\n"
    "{premium_emoji} <b>Премиум-ветка</b> — {premium_status}\n"
    "{premium_line}"
)
PASS_PROGRESS_LINE = " {percent}% ({have}/{need} до след. уровня)"
PASS_PREMIUM_ACTIVE = "✅ открыта"
PASS_PREMIUM_LOCKED = "🔒 закрыта"
PASS_NO_SEASON = "Сейчас нет активного сезона."

PASS_REWARD_PENDING = "Готово к получению: <b>{dust}</b> пыли, <b>{tickets}</b> тикетов."
PASS_REWARD_PENDING_PREMIUM = "Готово к получению: <b>{dust}</b> пыли, <b>{tickets}</b> тикетов, <b>{coins}</b> коинов."
PASS_REWARD_NONE = "Нечего забирать — повышайте уровень."
PASS_REWARD_LOCKED = "Купите пасс, чтобы открыть эту ветку."

BTN_PASS_CLAIM_FREE = "🎁 Забрать бесплатные награды"
BTN_PASS_CLAIM_PREMIUM = "💎 Забрать премиум-награды"
BTN_PASS_BUY = "🛒 Купить Battle Pass"
BTN_PASS_LEVELS = "📜 Все уровни"
BTN_PASS_APP = "🎫 Battle Pass (веб)"

PASS_CLAIM_FREE_DONE = "✅ Получено: {dust} пыли, {tickets} тикетов."
PASS_CLAIM_PREMIUM_DONE = "✅ Получено: {dust} пыли, {tickets} тикетов, {coins} коинов."
PASS_CLAIM_NONE = "Пока нечего забирать — повышай уровень."
PASS_CLAIM_NOT_PREMIUM = "Премиум-ветка закрыта — купите Battle Pass."

# --- Лента уровней (📜 Все уровни) ---
PASS_LEVELS_TITLE = "📜 <b>Все уровни</b> — стр. {page}/{total_pages} (тек. уровень {current_level})\n\n"
PASS_LEVELS_NO_SEASON = "Сейчас нет активного сезона."
PASS_LEVEL_ICON_LOCKED = "🔒"
PASS_LEVEL_ICON_READY = "🎁"
PASS_LEVEL_ICON_CLAIMED = "✅"
PASS_LEVEL_LINE = "{icon} <b>Ур. {level}</b> — Free: {free_dust}✨{free_tickets} | Premium: +{premium_dust}✨{premium_tickets}{premium_coins}\n"
PASS_LEVEL_TICKETS_PART = " {tickets}🎫"
PASS_LEVEL_COINS_PART = " {coins}💎"
BTN_PASS_PAGE_PREV = "◀️"
BTN_PASS_PAGE_NEXT = "▶️"
BTN_PASS_CLAIM_ALL = "🎁 Забрать всё"
BTN_PASS_BACK = "◀️ К пассу"
