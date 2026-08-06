"""callback_data и прочие строковые ключи домена "Колода" — заданы один раз здесь и
переиспользуются и в клавиатурах (кто строит кнопку), и в хендлерах (кто её матчит),
чтобы поменять формат в одном месте и не разъехаться."""

from __future__ import annotations

CB_DECK_OPEN = "deck:open"
CB_DECK_ROLL1 = "deck:roll1"
CB_DECK_CHANCES = "deck:chances"
CB_DECK_CHANCES_TIER_PREFIX = "deck:chances_tier:"
# Отдельно от CB_DECK_CHANCES: вход в "Шансы" из "Колоды" открывает НОВОЕ сообщение (как
# и остальные экраны колоды), а кнопка "К шансам" из детального экрана тира должна
# редактировать то же сообщение на месте, а не плодить дубликаты — разным поведением
# нужны разные callback'и на один и тот же контент обзора.
CB_DECK_CHANCES_BACK = "deck:chances_back"
CB_DECK_COLLECTION = "deck:collection"

# Ключ антидубликат-лока (см. cache/lock.py) для кнопки "Крутить".
LOCK_ACTION_ROLL = "roll"
