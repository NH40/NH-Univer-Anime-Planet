from __future__ import annotations

BTN_RENAME = "✏️ Сменить имя"
BTN_REFERRALS = "🔗 Рефералы"
BTN_DAILY_BONUS = "🎁 Ежедневный бонус"

PROFILE_CARD = (
    "👤 <b>Профиль</b>\n\n"
    "<b>Имя:</b> {name}\n"
    "<b>Username:</b> {username}\n"
    "<b>Клан:</b> {clan}\n\n"
    "{divider}\n\n"
    "⭐ <b>UBP за сезон:</b> {ubp_season}\n"
    "🏆 <b>UBP за всё время:</b> {ubp_total}\n"
    "📊 <b>Топ:</b> {rank}\n\n"
    "{divider}\n\n"
    "{tickets_line}\n"
    "🎴 <b>Круток за всё время:</b> {total_rolls}\n\n"
    "{divider}\n\n"
    "{progress}"
)
NO_USERNAME = "—"
NO_CLAN = "нет клана"
NO_RANK = "—"

PROGRESS_HEADER = "📚 <b>Прогресс по вселенным</b>\n"
PROGRESS_LINE = "🌌 <b>{universe}</b>\n{bar} {percent}% ({owned}/{total})\n"
# Разворачиваемая цитата Telegram — список вселенных по умолчанию свёрнут (особенно
# заметно, когда вселенных много), игрок разворачивает сам, если нужно (см. запрос
# пользователя 2026-08-06).
PROGRESS_QUOTE_OPEN = "<blockquote expandable>"
PROGRESS_QUOTE_CLOSE = "</blockquote>"
PROGRESS_EMPTY = "📚 Пока нет ни одной карты — крутите в «Колоде»!"

TICKETS_LINE_READY = "🎫 <b>Тикеты:</b> {count}/{cap} (бесплатный лимит заполнен)"
TICKETS_LINE_COUNTDOWN = "🎫 <b>Тикеты:</b> {count}/{cap} (следующий через {mm:02d}:{ss:02d})"

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
    "первой крутки, плюс {cut_percent}% с каждого его доната — пока действует связь."
)

RENAME_PROMPT = "Введите новое имя (2-32 символа, без переносов строк). /cancel — отменить."
RENAME_INVALID = "Некорректное имя: от 2 до 32 символов, без переносов строк. Попробуйте ещё раз."
RENAME_DONE = "Имя обновлено: {name}"
RENAME_CANCELLED = "Смена имени отменена."

TOP_HEADER = "🏆 <b>Топ-10 игроков сезона</b>\n\n"
TOP_LINE = "{place}. {name} — <b>{ubp}</b> UBP\n"
TOP_EMPTY = "Пока никто не набрал UBP в этом сезоне."

PLAYERS_HEADER = "📋 <b>Рейтинг игроков</b> (стр. {page}/{total_pages})\n\n"
PLAYERS_LINE = "{place}. {name} (@{username}) — <b>{ubp}</b> UBP\n"
PLAYERS_EMPTY = "Рейтинг пока пуст."
