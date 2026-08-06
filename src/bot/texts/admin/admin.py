from __future__ import annotations

ADMIN_MENU = "🛠 <b>Админ-панель</b>"
BTN_ADMIN_TECH_MODE = "🛠 Техрежим: {status}"
BTN_ADMIN_STATS = "📊 Статистика"
BTN_ADMIN_FIND_PLAYER = "🔍 Найти игрока"
BTN_ADMIN_SEASON = "🗓 Сезон"
BTN_ADMIN_PROMO = "🎟 Промокоды"
BTN_ADMIN_REFERRAL = "🔗 Рефералы"
BTN_ADMIN_BROADCAST = "📣 Рассылка"
BTN_ADMIN_MASS_GRANT = "🎁 Выдать всем"
BTN_ADMIN_DELETE_ACCOUNT = "🗑 Удалить аккаунт"
BTN_ADMIN_MANAGE_ADMINS = "👑 Админы"
BTN_ADMIN_WIPE = "💣 Обнулить БД"
BTN_ADMIN_EVENTS = "🎉 Ивенты"

TECH_MODE_ENABLED = "🛠 Техрежим включён."
TECH_MODE_DISABLED = "✅ Техрежим выключен."

STATS_SCREEN = (
    "📊 <b>Статистика</b>\n\n"
    "👥 Игроков всего: <b>{total_users}</b>\n"
    "🟢 Онлайн (24ч): <b>{online_users}</b>\n\n"
    "💎 Донатов: <b>{payments_count}</b> шт. на <b>{payments_rub}</b>₽\n\n"
    "🖥 CPU: {cpu_percent:.0f}%\n"
    "🧠 RAM: {ram_used_mb}/{ram_total_mb} МБ ({ram_percent:.0f}%)\n"
    "💾 Диск: {disk_used_gb:.1f}/{disk_total_gb:.1f} ГБ ({disk_percent:.0f}%)"
)

FIND_PLAYER_PROMPT = "Введите username (с @ или без) или id игрока. /cancel — отменить."
FIND_PLAYER_NOT_FOUND = "Игрок не найден."
ACTION_CANCELLED = "Отменено."

PLAYER_CARD = (
    "👤 <b>{name}</b> (id <code>{id}</code>{username})\n\n"
    "UBP сезона: {ubp_season}\n"
    "UBP всего: {ubp_total}\n"
    "Пыль: {dust}\n"
    "Коины: {coins}\n"
    "Клан: {clan}\n"
    "Статус: {status}"
)
STATUS_BANNED = "⛔️ Забанен"
STATUS_ACTIVE = "Активен"
NO_CLAN = "—"

BTN_GIVE_DUST = "✨ Выдать пыль"
BTN_GIVE_COINS = "💎 Выдать коины"
BTN_GIVE_CARD = "🃏 Выдать карточку"
BTN_BAN = "⛔️ Забанить"
BTN_UNBAN = "✅ Разбанить"
BTN_FIND_ANOTHER = "🔍 Другой игрок"

GIVE_DUST_PROMPT = "Сколько пыли выдать? /cancel — отменить."
GIVE_COINS_PROMPT = "Сколько коинов выдать? /cancel — отменить."
GIVE_CARD_PROMPT = (
    "Введите id карты, звёзды и количество через пробел, например: <code>5 1 3</code>. "
    "/cancel — отменить."
)
GIVE_AMOUNT_INVALID = "Нужно целое число больше 0."
GIVE_CARD_INVALID = "Формат: id_карты звёзды количество, все — целые числа больше 0."
GIVE_CARD_NOT_FOUND = "Карта с таким id не найдена."

GIVE_DUST_DONE = "✅ Выдано {amount} пыли игроку {name}."
GIVE_COINS_DONE = "✅ Выдано {amount} коинов игроку {name}."
GIVE_CARD_DONE = "✅ Выдана карта «{card_name}» {stars}★ x{qty} игроку {name}."
BAN_DONE = "⛔️ {name} забанен."
UNBAN_DONE = "✅ {name} разбанен."

# --- Сезон ---
SEASON_SCREEN = (
    "🗓 <b>Сезон</b>\n\n"
    "Текущая версия: <b>{version}</b>\n"
    "Начат: {started_at}"
)
SEASON_NONE = "🗓 <b>Сезон</b>\n\nАктивного сезона нет."
BTN_SEASON_NEW = "🔄 Новый сезон (сброс UBP)"
BTN_SEASON_BUMP_VERSION = "🔢 Сменить версию (без сброса)"
SEASON_NEW_PROMPT = (
    "Введите версию НОВОГО сезона (например 1.1, до 16 символов). "
    "Обнулит UBP сезона всем игрокам и раздаст награды топ-10. /cancel — отменить."
)
SEASON_BUMP_PROMPT = "Введите новую версию (например 1.0.1) — сезон НЕ обнулится. /cancel — отменить."
SEASON_VERSION_INVALID = "Версия должна быть непустой строкой до 16 символов."
SEASON_NEW_CONFIRM = "Точно начать новый сезон «{version}»? UBP сезона обнулится у ВСЕХ игроков, топ-10 получит награду."
BTN_CONFIRM = "✅ Подтвердить"
SEASON_NEW_DONE = "✅ Новый сезон «{version}» начат. Награду получили: {count} игроков."
SEASON_BUMP_DONE = "✅ Версия обновлена: {version}."

# --- Промокоды ---
PROMO_SCREEN = "🎟 <b>Промокоды</b>"
BTN_PROMO_CREATE = "➕ Создать промокод"
PROMO_CREATE_PROMPT = (
    "Введите промокод 4 строками:\n"
    "1) код (латиница/цифры, до 32 симв.)\n"
    "2) тип: <code>uses</code> (лимит активаций) / <code>time</code> (дней действия) / <code>users</code> (список username)\n"
    "3) параметр: число активаций, или число дней, или username через запятую\n"
    "4) награда: <code>пыль коины тикеты</code> (целые числа, 0 если не нужно)\n\n"
    "Например:\n<code>SUMMER2026\nuses\n100\n50 0 5</code>\n\n/cancel — отменить."
)
PROMO_CREATE_INVALID = "Не разобрал формат — см. подсказку выше, ровно 4 строки."
PROMO_CREATE_TAKEN = "Такой код уже существует."
PROMO_CREATE_DONE = "✅ Промокод «{code}» создан."

# --- Активация промокода (игрок) ---
PROMO_REDEEM_PROMPT = "Введите промокод. /cancel — отменить."
PROMO_NOT_FOUND = "Промокод не найден."
PROMO_EXPIRED = "Срок действия промокода истёк."
PROMO_NOT_ALLOWED = "Этот промокод не для вас."
PROMO_USES_EXHAUSTED = "Промокод исчерпан."
PROMO_ALREADY_REDEEMED = "Вы уже активировали этот промокод."
PROMO_REDEEM_DONE = "✅ Промокод активирован! Получено: {dust} пыли, {coins} коинов, {tickets} тикетов."

# --- Рефералы: список кампаний -> кнопка с названием -> детальная статистика ---
REFERRAL_SCREEN = "🔗 <b>Реферальные ссылки</b>"
REFERRAL_CHOOSE = "Выбери кампанию:"
REFERRAL_EMPTY = "Ссылок пока нет."
BTN_REFERRAL_CREATE = "➕ Создать ссылку"
REFERRAL_CREATE_PROMPT = "Введите название кампании (латиница/цифры/подчёркивания, до 32 симв.). /cancel — отменить."
REFERRAL_CREATE_INVALID = "Только латиница, цифры и подчёркивания, до 32 символов."
REFERRAL_CREATE_TAKEN = "Кампания с таким названием уже существует."
REFERRAL_CREATE_DONE = "✅ Ссылка создана:\n{url}"

REFERRAL_DETAIL_SCREEN = (
    "🔗 <b>Кампания «{code}»</b>\n\n"
    "<code>{url}</code>\n\n"
    "<b>Перешло:</b> {visited}\n"
    "<b>Играет:</b> {playing}\n"
    "<b>Подписок куплено:</b> {subscriptions_bought}\n"
    "<b>Battle Pass куплено:</b> {battle_passes_bought}\n\n"
    "💰 <b>Донат:</b> {donated_coins}₽"
)
REFERRAL_DETAIL_NOT_FOUND = "Кампания не найдена — возможно, экран устарел."

# --- Рассылка ---
BROADCAST_PROMPT = "Введите текст рассылки (уйдёт всем игрокам). /cancel — отменить."
BROADCAST_CONFIRM = "Разослать это сообщение ВСЕМ игрокам ({count} чел.)?\n\n---\n{text}"
BROADCAST_STARTED = "📣 Рассылка начата в фоне: {count} получателей."
BROADCAST_DONE = "📣 Рассылка «{preview}» завершена: доставлено {sent}, не доставлено {failed}."

# --- Массовые выдачи ---
MASS_GRANT_SCREEN = "🎁 <b>Выдать всем игрокам</b>"
BTN_MASS_GRANT_DUST = "✨ Пыль"
BTN_MASS_GRANT_COINS = "💎 Коины"
BTN_MASS_GRANT_TICKETS = "🎫 Тикеты"
MASS_GRANT_AMOUNT_PROMPT = "Сколько {currency} выдать КАЖДОМУ игроку? /cancel — отменить."
MASS_GRANT_CONFIRM = "Выдать {amount} {currency} ВСЕМ игрокам ({count} чел.)?"
MASS_GRANT_DONE = "✅ Выдано {amount} {currency} игрокам: {count} чел."
CURRENCY_DUST = "пыли"
CURRENCY_COINS = "коинов"
CURRENCY_TICKETS = "тикетов"

# --- Удаление аккаунта ---
DELETE_ACCOUNT_PROMPT = "Введите username или id игрока для полного удаления. /cancel — отменить."
DELETE_ACCOUNT_CONFIRM = (
    "⚠️ Точно ПОЛНОСТЬЮ удалить аккаунт {name} (id {id})? Это необратимо и сотрёт все "
    "данные игрока (карточки, прогресс, кланы, платежи, транзакции)."
)
DELETE_ACCOUNT_OWNER_BLOCKED = (
    "{name} — владелец клана «{clan_name}». Сначала передайте клан другому участнику "
    "или распустите клан (если он там один)."
)
DELETE_ACCOUNT_DONE = "🗑 Аккаунт {name} (id {id}) удалён."

# --- Управление админами (только для супер-админов из ADMIN_IDS) ---
MANAGE_ADMINS_HEADER = "👑 <b>Администраторы</b>\n\nСупер-админы (ADMIN_IDS в .env) сюда не входят.\n\n"
MANAGE_ADMINS_LINE = "• {name} (id <code>{id}</code>{username})\n"
MANAGE_ADMINS_EMPTY = "Пока нет ни одного дополнительного админа."
BTN_MANAGE_FIND_PLAYER = "🔍 Найти игрока"
MANAGE_FIND_PLAYER_PROMPT = "Введите username (с @ или без) или id игрока. /cancel — отменить."

MANAGE_ADMIN_CARD = "👤 <b>{name}</b> (id <code>{id}</code>{username})\n\n<b>Права админа:</b> {status}"
BTN_GRANT_ADMIN = "👑 Выдать админку"
BTN_REVOKE_ADMIN = "❌ Забрать админку"

ADMIN_GRANTED = "✅ {name} теперь администратор."
ADMIN_REVOKED = "❌ У {name} забраны права администратора."
NOTIFY_ADMIN_GRANTED = "👑 Вам выданы права администратора. Откройте /admin."
NOTIFY_ADMIN_REVOKED = "❌ У вас отозваны права администратора."
NOT_SUPER_ADMIN = "Эта функция доступна только главному администратору."

# --- Полное удаление БД (только для супер-админов из ADMIN_IDS) ---
WIPE_CONFIRM_PROMPT = (
    "💣 <b>Полный сброс базы данных</b>\n\n"
    "Это удалит ВСЕ данные ВСЕХ игроков без возможности восстановления: карточки, "
    "прогресс, кланы, платежи, транзакции — всё. Бот перезапустится с чистого листа.\n\n"
    "Нажмите «Подтвердить» ещё раз в течение 30 секунд, чтобы выполнить сброс."
)
WIPE_CONFIRM_EXPIRED = "Время подтверждения истекло. Начните заново."
WIPE_DONE = "💣 База данных полностью очищена. Бот работает с чистого листа."
WIPE_DONE_BROADCAST = "💣 База данных полностью очищена администратором @{name}."

# --- Ивенты (доступно любому админу) ---
EVENTS_HEADER = (
    "🎉 <b>Ивенты</b>\n\n"
    "Активен максимум один ивент одновременно. Пока ивент активен — у каждой крутки есть "
    "{chance:.2f}% шанс получить ивент-карту (7000 UBP) вместо обычной.\n\n"
)
EVENT_STATUS_LINE = "{icon} {title}\n"
EVENT_ACTIVE_ICON = "🟢"
EVENT_INACTIVE_ICON = "⚪"
BTN_EVENT_ACTIVATE_PREFIX = "▶️ Включить: "
BTN_EVENT_DEACTIVATE_PREFIX = "⏹ Выключить: "
EVENT_TOGGLED_ON = "✅ Ивент «{title}» включён."
EVENT_TOGGLED_OFF = "❌ Ивент «{title}» выключен."
