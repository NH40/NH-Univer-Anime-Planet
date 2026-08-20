from __future__ import annotations

# --- Общее / без клана ---
ACTION_CANCELLED = "Отменено."
NO_CLAN_SCREEN = "🏰 <b>Клан</b>\n\nУ тебя пока нет клана."
BTN_CREATE_CLAN = "➕ Создать клан"
BTN_FIND_CLAN = "🔍 Найти клан"
BTN_MY_INVITES = "✉️ Мои приглашения ({count})"

CREATE_CLAN_PROMPT = "Введите название клана ({min}-{max} символов)."
CREATE_CLAN_INVALID = "Название должно быть от {min} до {max} символов, без переносов строк."
CREATE_CLAN_TAKEN = "Клан с таким названием уже существует."
CREATE_CLAN_ALREADY_IN_CLAN = "Вы уже состоите в клане."
CREATE_CLAN_DONE = "✅ Клан «{name}» создан!"

# --- Карточка клана ---
CLAN_CARD = (
    "🏰 <b>{name}</b>{owner_crown}\n"
    "{description}\n"
    "👥 Участников: <b>{member_count}/{max_members}</b>\n"
    "⭐ UBP сезона: <b>{ubp_season}</b>\n"
    "🏆 UBP за всё время: <b>{ubp_total}</b>\n"
    "👑 Владелец: {owner_name}"
)
NO_DESCRIPTION = "Описание не добавлено.\n"
BTN_MEMBERS = "👥 Участники"
BTN_REQUESTS = "📬 Заявки ({count})"
BTN_INVITE = "✉️ Пригласить"
BTN_RANKS = "🎖 Ранги"
BTN_EDIT = "✏️ Редактировать"
BTN_EXCHANGE = "🔄 Обменник"
BTN_WAR = "⚔️ Война"
BTN_LEAVE = "🚪 Покинуть клан"
BTN_APPLY = "📨 Подать заявку"
BTN_CANCEL_APPLICATION = "❌ Отменить заявку"
ALREADY_APPLIED = "Заявка уже отправлена."
ALREADY_APPLIED_ELSEWHERE = "Вы уже подали заявку в другой клан — сначала отмените её."

# --- Поиск клана ---
FIND_CLANS_HEADER = "🔍 <b>Кланы</b> (стр. {page}/{total_pages})\n\n"
FIND_CLANS_LINE = "{place}. {name} — {ubp} UBP, {members} уч.\n"
FIND_CLANS_EMPTY = "Кланов пока нет — стань первым, кто создаст клан!"

# --- Участники ---
MEMBERS_HEADER = "👥 <b>Участники «{name}»</b>\n\n"
MEMBERS_LINE = "{rank_emoji} {name} (@{username}) — {rank_name}\n"
RANK_EMOJI = {"owner": "👑", "deputy": "🥈", "captain": "🎖", "member": "👤"}
RANK_NAME = {"owner": "Владелец", "deputy": "Заместитель", "captain": "Капитан", "member": "Участник"}

# --- Заявки (владелец/зам) ---
REQUESTS_HEADER = "📬 <b>Заявки в клан</b>\n\n"
REQUESTS_EMPTY = "Заявок пока нет."
REQUEST_LINE = "@{username}"
BTN_ACCEPT = "✅ Принять @{username}"
BTN_REJECT = "❌ Отклонить @{username}"
REQUEST_ACCEPTED = "✅ @{username} принят(а) в клан."
REQUEST_REJECTED = "❌ Заявка @{username} отклонена."
CLAN_FULL = "В клане уже максимум участников ({max})."
NOTIFY_NEW_APPLICATION = "📬 @{username} подал(а) заявку в клан «{clan_name}»."

# --- Приглашение игрока ---
INVITE_PROMPT = "Введите @username игрока, которого хотите пригласить."
INVITE_USER_NOT_FOUND = "Игрок с таким username не найден (он должен хотя бы раз запустить бота)."
INVITE_ALREADY_IN_CLAN = "Этот игрок уже состоит в клане."
INVITE_SENT = "✅ Приглашение отправлено @{username}."
NOTIFY_INVITE_RECEIVED = "✉️ Клан «{clan_name}» приглашает тебя вступить!"

# --- Мои приглашения (игрок) ---
MY_INVITES_HEADER = "✉️ <b>Приглашения в кланы</b>\n\n"
MY_INVITES_EMPTY = "Приглашений пока нет."
BTN_ACCEPT_INVITE = "✅ Вступить в «{clan_name}»"
BTN_DECLINE_INVITE = "❌ Отклонить «{clan_name}»"
INVITE_ACCEPTED = "✅ Добро пожаловать в «{clan_name}»!"
INVITE_DECLINED = "Приглашение отклонено."

# --- Ранги ---
RANKS_HEADER = "🎖 <b>Ранги «{name}»</b>\n\nВыбери участника:"
RANK_MEMBER_LINE = "{rank_emoji} {name}"
RANK_SET_MENU = "{name} — текущий ранг: {rank_name}\nНазначить:"
RANK_SET_DONE = "✅ {name} теперь {rank_name}."
CANNOT_CHANGE_OWNER_RANK = "Ранг владельца меняется только через передачу клана."

# --- Передача владения ---
BTN_TRANSFER = "👑 Передать клан"
TRANSFER_PROMPT = "Выбери, кому передать клан:"
TRANSFER_CONFIRM = "Точно передать клан «{clan_name}» игроку {name}? Вы станете обычным участником."
TRANSFER_DONE = "✅ Клан передан {name}."

# --- Редактирование ---
EDIT_MENU = "✏️ <b>Редактирование клана</b>"
BTN_EDIT_NAME = "Название"
BTN_EDIT_DESCRIPTION = "Описание"
BTN_EDIT_IMAGE = "Картинка"
EDIT_NAME_PROMPT = "Введите новое название клана ({min}-{max} символов)."
EDIT_NAME_DONE = "✅ Название обновлено."
EDIT_DESCRIPTION_PROMPT = "Введите новое описание клана (до {max} символов)."
EDIT_DESCRIPTION_TOO_LONG = "Слишком длинное описание (максимум {max} символов)."
EDIT_DESCRIPTION_DONE = "✅ Описание обновлено."
EDIT_IMAGE_NOT_ELIGIBLE = "Картинку клана может ставить только топ-{n} по UBP за всё время."
EDIT_IMAGE_PROMPT = "Отправьте картинку клана."
EDIT_IMAGE_DONE = "✅ Картинка клана обновлена."
NOT_AUTHORIZED = "Недостаточно прав."

# --- Обменник (пыль/тикеты/коины между участниками одного клана) ---
BTN_EXCHANGE_DUST = "✨ Пыль"
BTN_EXCHANGE_TICKETS = "🎫 Тикеты"
BTN_EXCHANGE_COINS = "💎 Коины"

# Флоу переработан (2026-08-14): было "выбор валюты -> ввести @username и число текстом",
# теперь "выбор игрока из списка -> выбор ресурса -> ввести только число" — не нужно помнить
# username вручную, и на каждом шаге есть кнопка "Назад" (подтверждено пользователем).
EXCHANGE_CHOOSE_MEMBER = "🔄 <b>Обменник</b>\n\nКому передать ресурс?"
EXCHANGE_NO_MEMBERS = "В клане больше никого нет — обмениваться не с кем."
EXCHANGE_CHOOSE_CURRENCY = "🔄 <b>Обменник</b> — {name}\n\nЧто передать?"
EXCHANGE_TARGET_GONE = "Этот игрок уже не в вашем клане — выберите другого."

# Родительный падеж множественного числа — одинаково подходит и для "количество {currency}",
# и для "Передано {amount} {currency}" (см. CLAUDE.md, "Кланы" — обменник обобщён с пыли
# на 3 валюты). Ключ — значение TransactionCurrency.
CURRENCY_NAMES_GENITIVE = {"dust": "пыли", "tickets": "тикетов", "coins": "коинов"}

EXCHANGE_PROMPT = "Сколько {currency} передать игроку {name}?\nНапример: <code>50</code>"
EXCHANGE_INVALID = "Нужно целое число больше 0. Попробуйте ещё раз."
EXCHANGE_NOT_IN_CLAN = "Этот игрок не в вашем клане."
EXCHANGE_NOT_ENOUGH = "Не хватает {currency}: нужно {needed}."
EXCHANGE_DONE = "✅ Передано {amount} {currency} игроку @{username}."
NOTIFY_EXCHANGE_RECEIVED = "🔄 Вам передали {amount} {currency} от @{username}."

# --- Война ---
WAR_NONE = "⚔️ Сейчас клан ни с кем не воюет."
BTN_START_WAR = "⚔️ Объявить войну"
WAR_ACTIVE = (
    "⚔️ <b>Война!</b>\n\n"
    "{name_a}: <b>{gained_a}</b> UBP\n"
    "{name_b}: <b>{gained_b}</b> UBP\n\n"
    "Окончание: {ends_at}"
)
WAR_FINISHED_WIN = "🏆 Война окончена! Победа клана «{winner}» — участникам начислено {reward} пыли."
WAR_FINISHED_DRAW = "🤝 Война окончена — ничья, награда не начислена."
WAR_ALREADY_AT_WAR = "Один из кланов уже воюет."
WAR_TARGET_PROMPT = "⚔️ Выбери клан для объявления войны:"
WAR_STARTED = "⚔️ Война с «{target}» началась! Длится {hours}ч."

# --- Покинуть клан ---
LEAVE_CONFIRM = "Точно хотите покинуть клан «{name}»?"
LEAVE_DONE = "Вы покинули клан."
LEAVE_MUST_TRANSFER = "Сначала передайте клан другому участнику (кнопка «Передать клан»), потом сможете выйти."
NOT_IN_CLAN = "Вы не состоите в клане."

# --- /topclan ---
TOPCLAN_HEADER = "🏆 <b>Топ кланов</b> ({mode}, стр. {page}/{total_pages})\n\n"
TOPCLAN_MODE_SEASON = "за сезон"
TOPCLAN_MODE_TOTAL = "за всё время"
BTN_TOPCLAN_TOGGLE_TOTAL = "🏆 За всё время"
BTN_TOPCLAN_TOGGLE_SEASON = "⭐ За сезон"
