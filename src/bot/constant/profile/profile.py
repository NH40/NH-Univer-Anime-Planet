from __future__ import annotations

CB_PROFILE_RENAME = "profile:rename"
CB_PLAYERS_PAGE_PREFIX = "players_page:"
CB_PROFILE_REFERRALS = "profile:referrals"
# Заглушка — см. TODO.md.
CB_PROFILE_DAILY_BONUS = "profile:daily_bonus"
# "Назад" с экрана рефералов (и других под-экранов профиля) — редактирует то же сообщение
# обратно в карточку профиля, тот же паттерн "_OPEN", что CB_DECK_OPEN/CB_SHOP_OPEN у
# остальных доменов.
CB_PROFILE_OPEN = "profile:open"

# --- /top: топ по вселенной (см. CLAUDE.md, "Топ по вселенной") --- Один комбинированный
# экран с двумя независимыми селекторами (вселенная + период) вместо жёсткого 2-шагового
# визарда — тап по любому из них перерисовывает список, сохраняя ВТОРОЙ выбор как есть.
# Кодируем оба значения в одном callback_data, чтобы хендлер был один на оба селектора.
CB_TOP_PREFIX = "top:"
TOP_SCOPE_SEASON = "season"
TOP_SCOPE_TOTAL = "total"
