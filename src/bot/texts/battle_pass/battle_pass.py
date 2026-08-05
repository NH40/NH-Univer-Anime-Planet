from __future__ import annotations

PASS_SCREEN = (
    "🎫 <b>Сезонный пасс</b>\n\n"
    "<b>Уровень:</b> {level}/{max_level}\n"
    "{bar}{progress}\n"
    "<b>UBP сезона:</b> {ubp_season}\n\n"
    "🎁 <b>Бесплатная ветка</b>\n"
    "{free_line}\n\n"
    "{premium_emoji} <b>Премиум-ветка</b> — {premium_status}\n"
    "{premium_line}"
)
PASS_PROGRESS_LINE = " {percent}% ({have}/{need} UBP до след. уровня)"
PASS_MAX_LEVEL_LINE = " Максимальный уровень!"
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

PASS_CLAIM_FREE_DONE = "✅ Получено: {dust} пыли, {tickets} тикетов."
PASS_CLAIM_PREMIUM_DONE = "✅ Получено: {dust} пыли, {tickets} тикетов, {coins} коинов."
PASS_CLAIM_NONE = "Пока нечего забирать — повышай уровень."
PASS_CLAIM_NOT_PREMIUM = "Премиум-ветка закрыта — купите Battle Pass."
