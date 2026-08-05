from __future__ import annotations

import logging

from aiogram import Bot
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.game import (
    NOTIFY_ROLL_REMINDER_INTERVAL_SECONDS,
    SUBSCRIPTION_DAILY_TICKET_INTERVAL_SECONDS,
    SUBSCRIPTION_DAILY_TICKETS,
    TICKET_NATURAL_CAP,
    TICKET_REGEN_INTERVAL_SECONDS_SUBSCRIBED,
)
from bot.texts.notify import ROLL_REMINDER, TICKETS_FULL_REMINDER
from bot.utils.notify import notify

log = logging.getLogger(__name__)

# Как часто фоновый таск (см. main.py) опрашивает БД — не игровой баланс (правило 8 про
# config/game — это шансы/лимиты/формулы), а инженерный компромисс между своевременностью
# пушей и нагрузкой на Postgres. В проекте до этого не было фонового шедулера вообще —
# всё остальное либо реагирует на действие игрока, либо считается лениво при заходе на
# экран (см. CLAUDE.md, кланы/войны). Пуши по таймеру физически не могут быть ленивыми —
# игрок должен получить их, даже если не открывает бота.
SWEEP_INTERVAL_SECONDS = 300

_GRANT_SUBSCRIPTION_TICKETS_SQL = text(
    """
    WITH due AS (
        SELECT
            id,
            FLOOR(EXTRACT(EPOCH FROM (now() - subscription_ticket_granted_at)) / :interval)::int AS periods
        FROM users
        WHERE subscription_until > now()
          AND subscription_ticket_granted_at IS NOT NULL
          AND subscription_ticket_granted_at <= now() - (:interval * INTERVAL '1 second')
        FOR UPDATE
    )
    UPDATE users
    SET tickets_count = users.tickets_count + due.periods * :amount,
        subscription_ticket_granted_at = users.subscription_ticket_granted_at + (due.periods * :interval) * INTERVAL '1 second'
    FROM due
    WHERE users.id = due.id
    RETURNING users.id
    """
)

_FIND_TICKETS_FULL_SQL = text(
    """
    UPDATE users
    SET tickets_updated_at = now()
    WHERE notify_tickets_full = true
      AND subscription_until > now()
      AND tickets_count >= :cap
      AND tickets_updated_at <= now() - (:interval * INTERVAL '1 second')
    RETURNING id
    """
)

_FIND_ROLL_REMINDER_SQL = text(
    """
    UPDATE users
    SET roll_reminder_sent_at = now()
    WHERE notify_roll_reminder = true
      AND roll_reminder_sent_at <= now() - (:interval * INTERVAL '1 second')
    RETURNING id
    """
)


async def grant_subscription_tickets(session: AsyncSession) -> list[int]:
    """Начисляет всем активным подписчикам +5 тикетов за каждые полные 24ч, прошедшие с
    прошлого начисления — копится по факту, если игрок долго не заходил (например, не был
    3 дня — придёт +15 разом), в отличие от обычного ленивого тикет-регена, который вместо
    этого "замораживается" на капе (см. CLAUDE.md, "Подписка" — это осознанно другое
    поведение, подтверждено пользователем 2026-08-05). Коммитит сама — самостоятельная
    операция, не часть чего-то большего. Возвращает id тех, кому начислили."""
    result = await session.execute(
        _GRANT_SUBSCRIPTION_TICKETS_SQL,
        {"interval": SUBSCRIPTION_DAILY_TICKET_INTERVAL_SECONDS, "amount": SUBSCRIPTION_DAILY_TICKETS},
    )
    ids = [row[0] for row in result.all()]
    await session.commit()
    return ids


async def find_and_notify_tickets_full(session: AsyncSession) -> list[int]:
    """Возвращает id подписчиков, у которых полный бак тикетов дольше часа (реген всё равно
    простаивает на капе) — и сразу "трогает" tickets_updated_at, ровно как это сделал бы
    обычный заход в приложение (см. CLAUDE.md, анти-эксплойт тикетов), иначе следующий
    проход шедулера напомнил бы повторно раньше чем через час. Коммитит сама."""
    result = await session.execute(
        _FIND_TICKETS_FULL_SQL,
        {"cap": TICKET_NATURAL_CAP, "interval": TICKET_REGEN_INTERVAL_SECONDS_SUBSCRIBED},
    )
    ids = [row[0] for row in result.all()]
    await session.commit()
    return ids


async def find_and_notify_roll_reminder(session: AsyncSession) -> list[int]:
    """Раз в 12 часов — напоминание "пора крутить", всем игрокам (не только подписчикам),
    у кого не отключено в настройках. Коммитит сама."""
    result = await session.execute(
        _FIND_ROLL_REMINDER_SQL, {"interval": NOTIFY_ROLL_REMINDER_INTERVAL_SECONDS}
    )
    ids = [row[0] for row in result.all()]
    await session.commit()
    return ids


async def run_sweep(bot: Bot, session: AsyncSession) -> None:
    """Единственная точка входа фонового таска (см. main.py). Единственное место в проекте,
    где сервисный слой сам зовёт Bot API (см. CLAUDE.md, правило 10) — у периодической
    задачи по таймеру нет хендлера, которому можно было бы делегировать I/O с Telegram."""
    await grant_subscription_tickets(session)

    tickets_full_ids = await find_and_notify_tickets_full(session)
    for user_id in tickets_full_ids:
        await notify(bot, user_id, TICKETS_FULL_REMINDER)

    roll_reminder_ids = await find_and_notify_roll_reminder(session)
    for user_id in roll_reminder_ids:
        await notify(bot, user_id, ROLL_REMINDER)

    log.info(
        "notify sweep: tickets_full=%d roll_reminder=%d", len(tickets_full_ids), len(roll_reminder_ids)
    )
