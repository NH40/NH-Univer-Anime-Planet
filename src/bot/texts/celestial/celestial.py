from __future__ import annotations

BTN_CELESTIAL_MENU = "🌌 Небесные карты"

CELESTIAL_LIST_HEADER = "🌌 <b>Небесные карты</b>\n\nВсего одна такая карта на весь бот — один владелец и максимум один претендент за раз.\n\n"
CELESTIAL_LIST_EMPTY = "Пока ни одна небесная карта не настроена."
CELESTIAL_LIST_BUTTON_FREE = "🆓 {name}"
CELESTIAL_LIST_BUTTON_OWNED = "👑 {name}"
CELESTIAL_LIST_BUTTON_CONTESTED = "⚔️ {name}"

CELESTIAL_DETAIL_HEADER = "🌌 <b>{name}</b> ({universe})\n"
CELESTIAL_DETAIL_FREE = "Ещё никем не найдена — выпадает с шансом на крутке в этой вселенной."
CELESTIAL_DETAIL_OWNER_LINE = "👑 Владелец: {name}\n"
CELESTIAL_DETAIL_CHALLENGER_LINE = "⚔️ Претендент: {name} (решение до {deadline})\n"
CELESTIAL_DETAIL_BATTLE_LINE = "⚔️ Идёт бой: игра {game_num}/{total_games} ({game}) — счёт побед {owner_wins}:{challenger_wins}\n"
CELESTIAL_DETAIL_YOUR_THROWS = "Ваши броски в этой игре: {count}/{max} (сумма {sum})\n"

BTN_CELESTIAL_ACCEPT = "✅ Принять бой"
BTN_CELESTIAL_DECLINE = "❌ Отказаться (карта уйдёт претенденту)"
BTN_CELESTIAL_THROW = "{emoji} Бросить ({game})"

CELESTIAL_ACCEPT_DONE = "⚔️ Бой начался! Первая игра — {emoji} {game}."
CELESTIAL_DECLINE_CONFIRM = "Точно отказаться? Карта сразу перейдёт претенденту без боя."
CELESTIAL_DECLINE_DONE = "Вы отказались от боя — карта перешла претенденту."
CELESTIAL_NOT_CHALLENGED_ALERT = "Сейчас нет ожидающего решения претендента на эту карту."
CELESTIAL_NO_BATTLE_ALERT = "Сейчас нет активного боя за эту карту."
CELESTIAL_NOT_PARTICIPANT_ALERT = "Вы не участник этого боя."
CELESTIAL_ALREADY_THREW_ALERT = "Вы уже сделали все броски в этой игре — ждите соперника."
CELESTIAL_GAME_EXPIRED_ALERT = "Время этой игры истекло — результат уже подводится."

GAME_NAMES = {
    "dice": "Кости",
    "darts": "Дартс",
    "football": "Футбол",
    "basketball": "Баскетбол",
    "bowling": "Боулинг",
}

# --- Пуш-уведомления (см. CLAUDE.md, "Небесные карты") ---
CELESTIAL_PUSH_NEW_OWNER = "🌌 Вам выпала небесная карта «{name}»! Вы стали её единственным владельцем."
CELESTIAL_PUSH_NEW_CHALLENGER_SELF = (
    "🌌 Вам выпала небесная карта «{name}»! Она уже у другого игрока — вы стали ПРЕТЕНДЕНТОМ. "
    "Ждите решения владельца (до {hours}ч)."
)
CELESTIAL_PUSH_NEW_CHALLENGE_OWNER = (
    "⚔️ На вашу небесную карту «{name}» претендует другой игрок! У вас {hours}ч, чтобы принять бой "
    "или отказаться — иначе карта автоматически уйдёт претенденту."
)
CELESTIAL_PUSH_LOST_TIMEOUT = "⏰ Вы не ответили вовремя — небесная карта «{name}» перешла претенденту."
CELESTIAL_PUSH_GAINED_TIMEOUT = "🌌 Владелец не ответил вовремя — небесная карта «{name}» теперь ваша!"
CELESTIAL_PUSH_LOST_DECLINE = "Владелец отказался от боя — небесная карта «{name}» теперь ваша!"

CELESTIAL_PUSH_BATTLE_STARTED = "⚔️ Бой за «{name}» начался! Игра 1/{total}: {emoji} {game}. У вас есть {hours}ч на 3 броска."
CELESTIAL_PUSH_NEXT_GAME = (
    "Игра завершена, счёт побед {owner_wins}:{challenger_wins}. Следующая игра {game_num}/{total}: "
    "{emoji} {game}. У вас есть {hours}ч на 3 броска."
)

CELESTIAL_PUSH_MATCH_WON_OWNER = "🏆 Вы отстояли небесную карту «{name}»! Претендент снят."
CELESTIAL_PUSH_MATCH_LOST_OWNER = "💔 Вы проиграли бой — небесная карта «{name}» перешла сопернику."
CELESTIAL_PUSH_MATCH_WON_CHALLENGER = "🏆 Вы выиграли бой — небесная карта «{name}» теперь ваша!"
CELESTIAL_PUSH_MATCH_LOST_CHALLENGER = "💔 Вы проиграли бой за «{name}» — карта осталась у владельца."

DIVINE_PUSH_UNIVERSE = "👑 Вы собрали всю обычную коллекцию вселенной «{universe}» — получена БОЖЕСТВЕННАЯ карта «{name}»!"
DIVINE_PUSH_GLOBAL = (
    "👑✨ Вы владеете ВСЕМИ небесными картами одновременно! Получена величайшая БОЖЕСТВЕННАЯ карта «{name}»!"
)
DIVINE_PUSH_PSEUDO = (
    "👑 Вы когда-то владели всеми небесными картами (пусть и не одновременно) — получена "
    "ПСЕВДО-БОЖЕСТВЕННАЯ карта «{name}»!"
)
