from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.cache.redis_client import make_redis, make_redis_pool
from bot.config.settings import get_settings
from bot.db.session import make_engine, make_session_factory
from bot.handlers import get_routers
from bot.logging_setup import setup_logging
from bot.middlewares.ban_check import BanCheckMiddleware
from bot.middlewares.command_state_reset import CommandStateResetMiddleware
from bot.middlewares.db_session import DbSessionMiddleware
from bot.middlewares.tech_mode import TechModeMiddleware
from bot.middlewares.throttling import ThrottlingMiddleware
from bot.services.notify import SWEEP_INTERVAL_SECONDS, run_sweep

log = logging.getLogger(__name__)


async def _notify_sweep_loop(bot: Bot, session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Единственный фоновый таск в проекте — раз в SWEEP_INTERVAL_SECONDS начисляет
    тикеты подписчикам и рассылает push-уведомления (см. services/notify, CLAUDE.md
    "Подписка"). Всё остальное в боте реагирует на действия игрока или считается лениво —
    это единственная работа, которая обязана случиться сама по себе, по таймеру."""
    while True:
        try:
            async with session_factory() as session:
                await run_sweep(bot, session)
        except Exception:
            log.exception("Notify sweep failed")
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    engine = make_engine(settings)
    session_factory = make_session_factory(engine)

    redis_pool = make_redis_pool(settings.redis_url)
    redis = make_redis(redis_pool)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    # FSM-состояния (например, ожидание нового имени) переживают рестарт бота —
    # хранятся в Redis, а не в памяти процесса.
    dp = Dispatcher(storage=RedisStorage(redis))

    throttle_mw = ThrottlingMiddleware(redis, settings.throttle_interval_ms)
    db_mw = DbSessionMiddleware(session_factory)
    tech_mw = TechModeMiddleware(redis, settings.admin_ids)
    ban_mw = BanCheckMiddleware()
    command_state_reset_mw = CommandStateResetMiddleware()

    # Порядок важен: throttle_mw — самый внешний, отсекает спам ДО открытия сессии БД
    # (незачем тратить соединение на апдейт, который всё равно будет отброшен). db_mw —
    # следующий, чтобы session была доступна tech_mw/ban_mw. Регистрируем как outer —
    # работают на все апдейты, даже если ни один хендлер не совпал по фильтрам (важно
    # для антифлуда/техрежима/бана).
    for observer in (dp.message, dp.callback_query):
        observer.outer_middleware(throttle_mw)
        observer.outer_middleware(db_mw)
        observer.outer_middleware(tech_mw)
        observer.outer_middleware(ban_mw)
    # Только Message — у callback_query команд не бывает. Сбрасывает "зависшее" FSM-
    # состояние на любую /команду, чтобы она не проглатывалась хендлером чужого
    # "ожидания ввода" (см. CLAUDE.md, баг "/promo триггерит обменник клана").
    dp.message.outer_middleware(command_state_reset_mw)

    dp.include_routers(*get_routers())

    sweep_task = asyncio.create_task(_notify_sweep_loop(bot, session_factory))

    try:
        log.info("Starting bot polling")
        await bot.delete_webhook(drop_pending_updates=True)
        # redis/session_factory передаём через workflow data — доступны как аргумент
        # любого хендлера. session_factory нужен фоновым таскам (рассылка), которым
        # нельзя переиспользовать `session` запроса — та закрывается вместе с хендлером.
        await dp.start_polling(bot, redis=redis, session_factory=session_factory)
    finally:
        sweep_task.cancel()
        try:
            await sweep_task
        except asyncio.CancelledError:
            pass
        await bot.session.close()
        await engine.dispose()
        await redis.aclose()
        await redis_pool.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
