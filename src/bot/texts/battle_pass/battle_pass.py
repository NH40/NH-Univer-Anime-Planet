from __future__ import annotations

PASS_NO_SEASON = "Сейчас нет активного сезона."

# --- Экран уровней (единственный экран пасса теперь, см. CLAUDE.md, "Сезонный пасс: клейм
# произвольной ячейки") — заголовок с прогрессом + сетка кнопок по уровням страницы. ---
PASS_HEADER = (
    "🎫 <b>Сезонный пасс</b> — уровень <b>{level}</b>\n"
    "{bar} {percent}% ({have}/{need} до след. уровня)\n"
    "{premium_status}\n"
    "{boost_line}\n\n"
    "Стр. {page}/{total_pages}. Жми на ячейку — заберёшь именно её награду.\n"
)
PASS_PREMIUM_ACTIVE = "💎 Премиум-ветка открыта"
PASS_PREMIUM_LOCKED = "🔒 Премиум-ветка закрыта — купите Battle Pass"

# Дневной буст прогресса (см. CLAUDE.md, "Сезонный пасс: 500 циклических уровней") — не
# влияет на UBP сезона, только на скорость заполнения самого пасса. ×1 = квота на сегодня
# исчерпана, показываем без "сброс через" интригующим множителем — просто когда обновится.
PASS_BOOST_LINE = "🚀 Буст: ×{multiplier} ({used}/{cap} ур. сегодня, сброс через {countdown})"

PASS_LEVEL_ICON_LOCKED = "🔒"
PASS_LEVEL_ICON_CLAIMED = "✅"
BTN_PASS_LEVEL_FREE = "{level} · {reward}"
BTN_PASS_LEVEL_PREMIUM = "💎{level} · {reward}"
PASS_LEVEL_REWARD_TICKETS = "🎫{tickets}"
PASS_LEVEL_REWARD_DUST = "✨{dust}"
PASS_LEVEL_REWARD_COINS_SUFFIX = "+💎{coins}"

BTN_PASS_PAGE_PREV = "◀️"
BTN_PASS_PAGE_NEXT = "▶️"
BTN_PASS_CLAIM_ALL_FREE = "🎁 Забрать всё (бесплатная)"
BTN_PASS_CLAIM_ALL_PREMIUM = "🎁 Забрать всё (премиум)"
BTN_PASS_BUY = "🛒 Купить Battle Pass"
BTN_PASS_APP = "🎫 Battle Pass (веб)"

PASS_CLAIMED_DONE = "✅ Уровень {level}: {reward}."
PASS_CLAIM_ALL_DONE = "🎁 Забрано уровней: {count}. Получено: {reward}."
PASS_REWARD_DUST_ONLY = "{dust} пыли"
PASS_REWARD_DUST_TICKETS = "{dust} пыли, {tickets} 🎫"
PASS_REWARD_TICKETS_ONLY = "{tickets} 🎫"
PASS_REWARD_COINS_SUFFIX = ", {coins} 💎"

PASS_LEVEL_LOCKED_ALERT = "Уровень ещё не открыт."
PASS_LEVEL_ALREADY_CLAIMED_ALERT = "Уже забрано."
PASS_NOT_PREMIUM_ALERT = "Премиум-ветка закрыта — купите Battle Pass."
PASS_NOTHING_TO_CLAIM_ALERT = "Нечего забирать — повышайте уровень."
