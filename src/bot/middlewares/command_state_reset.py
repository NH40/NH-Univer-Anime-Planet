from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

# /cancel уже штатно чистит state сама (см. каждый `cancel_*`-хендлер в проекте) — не
# нужно делать это дважды, и не нужно "съедать" апдейт до того, как её собственный
# хендлер отработает.
_EXEMPT_COMMANDS = {"/cancel"}


class CommandStateResetMiddleware(BaseMiddleware):
    """Любая слэш-команда, присланная пока висит незакрытое FSM-состояние (забыл /cancel
    посреди ввода — например, суммы обмена в клане или кода промокода), раньше молча
    проглатывалась хендлером ЭТОГО состояния как "невалидный ввод": хендлер повторял
    подсказку и НЕ чистил state, поэтому вообще ни одна команда (даже /promo, /start)
    не работала, пока игрок сам не догадается прислать /cancel (см. CLAUDE.md — баг
    "/promo триггерит обменник клана"). Сбрасываем состояние здесь, ДО того как апдейт
    дойдёт до роутеров/хендлеров конкретных FSM-флоу — тогда команда обрабатывается тем,
    для кого она реально предназначена, а не хендлером чужого "ожидания ввода"."""

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        text = event.text
        if text and text.startswith("/") and text.split()[0].lower() not in _EXEMPT_COMMANDS:
            state = data.get("state")
            if state is not None and await state.get_state() is not None:
                await state.clear()
        return await handler(event, data)
