"""callback_data и прочие строковые ключи домена "Колода" — заданы один раз здесь и
переиспользуются и в клавиатурах (кто строит кнопку), и в хендлерах (кто её матчит),
чтобы поменять формат в одном месте и не разъехаться."""

from __future__ import annotations

CB_DECK_OPEN = "deck:open"
CB_DECK_ROLL1 = "deck:roll1"
CB_DECK_ROLL10 = "deck:roll10"
CB_DECK_CHANCES = "deck:chances"
CB_DECK_COLLECTION = "deck:collection"

# Ключ антидубликат-лока (см. cache/lock.py) для кнопок "Крутить 1"/"Крутить 10" —
# общий на оба действия намеренно: они делят один и тот же баланс тикетов.
LOCK_ACTION_ROLL = "roll"
