from __future__ import annotations

BTN_RENAME = "✏️ Сменить имя"
BTN_REFERRALS = "🔗 Рефералы"
BTN_DAILY_BONUS = "🎁 Ежедневный бонус"

PROFILE_CARD = (
    "👤 <b>Профиль</b>\n\n"
    "<b>Имя:</b> {name}\n"
    "<b>Username:</b> {username}\n"
    "<b>Клан:</b> {clan}\n\n"
    "————— <b>РЕЙТИНГ:</b> —————\n\n"
    "⭐ <b>UBP за сезон:</b> {ubp_season}\n"
    "🏆 <b>UBP за всё время:</b> {ubp_total}\n"
    "🌌 <b>UBP вселенной ({universe}):</b> {universe_ubp}\n"
    "📊 <b>Топ:</b> {rank}\n\n"
    "————— <b>РЕСУРСЫ:</b> —————\n"
    "{tickets_line}\n"
    "🎴 <b>Круток за всё время:</b> {total_rolls}\n\n"
    "✨ <b>Пыль:</b> {dust}\n"
    "💎 <b>Коины:</b> {coins}\n\n"
    "{progress}"
)
NO_USERNAME = "—"
NO_CLAN = "нет клана"
NO_RANK = "—"
# Отдельная строка от общего "UBP за сезон" (см. CLAUDE.md, "Топ по вселенной") — только
# ТЕКУЩАЯ выбранная для крутки вселенная (User.universe_selected), не все сразу: у игрока
# может быть прогресс в нескольких вселенных, но профиль — не место для их перечисления
# (для этого есть отдельный /top по каждой).
NO_UNIVERSE_SELECTED = "вселенная не выбрана"

PROGRESS_HEADER = "📚 <b>Прогресс по вселенным</b>\n"
PROGRESS_LINE = "🌌 <b>{universe}</b>\n{bar} {percent}% ({owned}/{total})\n"
# Разворачиваемая цитата Telegram — список вселенных по умолчанию свёрнут (особенно
# заметно, когда вселенных много), игрок разворачивает сам, если нужно (см. запрос
# пользователя 2026-08-06).
PROGRESS_QUOTE_OPEN = "<blockquote expandable>"
PROGRESS_QUOTE_CLOSE = "</blockquote>"
PROGRESS_EMPTY = "📚 Пока нет ни одной карты — крутите в «Колоде»!"

TICKETS_LINE_READY = "🎫 <b>Тикеты:</b> {count}/{cap}"
TICKETS_LINE_COUNTDOWN = "🎫 <b>Тикеты:</b> {count}/{cap} (следующий через {time})"

REFERRALS_SCREEN = (
    "🔗 <b>Рефералы</b>\n\n"
    "Ваша персональная ссылка:\n<code>{link}</code>\n\n"
    "<b>Перешло:</b> {invited}\n"
    "<b>Играет:</b> {playing}\n"
    "<b>Донатеров:</b> {donors}\n"
    "<b>С подпиской:</b> {subscribers}\n"
    "<b>С Battle Pass:</b> {battle_pass_owners}\n\n"
    "💰 <b>Заработано с рефералов:</b> {coins_earned} коинов, {tickets_earned} тикетов\n\n"
    "За каждого приглашённого — {reward_coins} коинов и {reward_tickets} тикетов после его "
    "{threshold}-й крутки, плюс {cut_percent}% с каждого его доната — пока действует связь."
)

RENAME_PROMPT = "Введите новое имя (2-32 символа, без переносов строк)."
RENAME_INVALID = "Некорректное имя: от 2 до 32 символов, без переносов строк. Попробуйте ещё раз."
RENAME_DONE = "Имя обновлено: {name}"
RENAME_CANCELLED = "Смена имени отменена."

TOP_HEADER = "🏆 <b>Топ — {universe}</b> ({scope})\n\n"
TOP_LINE = "{place}. {name} — <b>{ubp}</b> UBP\n"
TOP_EMPTY = "Пока никто не набрал UBP в этой вселенной ({scope})."
TOP_SCOPE_SEASON_LABEL = "за этот сезон"
TOP_SCOPE_TOTAL_LABEL = "за всё время"
BTN_TOP_SCOPE_SEASON = "📅 За этот сезон"
BTN_TOP_SCOPE_TOTAL = "🏆 За все время"
# Только "за сезон" реально что-то раздаёт при смене сезона (см. services/season) — "за
# всё время" чисто информационный, ubp_total никогда не сбрасывается.
TOP_SEASON_REWARD_NOTE = "\nТоп-10 получит награду при смене сезона."
TOP_NO_ACTIVE_UNIVERSES = "Пока нет ни одной активной вселенной."

PLAYERS_HEADER = "📋 <b>Рейтинг игроков</b> (стр. {page}/{total_pages})\n\n"
PLAYERS_LINE = "{place}. {name} (@{username}) — <b>{ubp}</b> UBP\n"
PLAYERS_EMPTY = "Рейтинг пока пуст."
