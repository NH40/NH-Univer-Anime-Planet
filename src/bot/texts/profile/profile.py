from __future__ import annotations

BTN_RENAME = "✏️ Сменить имя"
BTN_REFERRALS = "🔗 Рефералы"
BTN_DAILY_BONUS = "🎁 Ежедневный бонус"

PROFILE_CARD = (
    "👤 <b>Профиль</b>\n\n"
    "Имя: {name}\n"
    "Username: {username}\n"
    "Клан: {clan}\n\n"
    "⭐ UBP за сезон: <b>{ubp_season}</b> (место в топе: {rank})\n"
    "🏆 UBP за всё время: <b>{ubp_total}</b>\n\n"
    "{tickets_line}\n"
    "🎴 Круток за всё время: <b>{total_rolls}</b>\n\n"
    "{progress}"
)
NO_USERNAME = "—"
NO_CLAN = "нет клана"
NO_RANK = "—"

PROGRESS_HEADER = "📚 <b>Прогресс по вселенным</b>\n"
PROGRESS_LINE = "🌌 {universe}: {bar} <b>{percent}%</b> ({owned}/{total})\n"
PROGRESS_EMPTY = "📚 Пока нет ни одной карты — крутите в «Колоде»!"

TICKETS_LINE_READY = "🎫 Тикеты: <b>{count}/{cap}</b> (бесплатный лимит заполнен)"
TICKETS_LINE_COUNTDOWN = "🎫 Тикеты: <b>{count}/{cap}</b> (следующий через {mm:02d}:{ss:02d})"

STUB_REFERRALS = "🔗 Раздел рефералов скоро появится."
STUB_DAILY_BONUS = "🎁 Ежедневный бонус скоро появится."

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
