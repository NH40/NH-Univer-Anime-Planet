from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.game import TICKET_NATURAL_CAP, TICKET_REGEN_INTERVAL_SECONDS, TICKET_REGEN_INTERVAL_SECONDS_SUBSCRIBED

# Один атомарный запрос: досчитывает лениво накопленный реген (с "заморозкой" таймера,
# пока баланс >= капа — см. CLAUDE.md, "Модель тикетов", про анти-эксплойт) и сразу же
# списывает :n (может быть 0 — тогда это просто "актуализировать и вернуть баланс").
# FOR UPDATE — блокирует строку от параллельного двойного клика на то же действие.
# Интервал регена — :interval_sub, пока подписка активна (subscription_until > now()),
# иначе :interval_normal (см. CLAUDE.md, "Подписка") — выражение продублировано дважды
# (для new_count и для сдвига tickets_updated_at), т.к. Postgres не даёт сослаться на
# алиас соседней колонки внутри того же SELECT.
_REGEN_AND_SPEND_SQL = text(
    """
    WITH regen AS (
        SELECT
            id,
            tickets_count AS old_count,
            tickets_updated_at AS old_ts,
            CASE WHEN subscription_until > now() THEN :interval_sub::int ELSE :interval_normal::int END AS effective_interval,
            CASE
                WHEN tickets_count >= :cap THEN tickets_count
                ELSE LEAST(
                    :cap,
                    tickets_count + FLOOR(
                        EXTRACT(EPOCH FROM (now() - tickets_updated_at)) /
                        (CASE WHEN subscription_until > now() THEN :interval_sub::int ELSE :interval_normal::int END)
                    )::int
                )
            END AS new_count
        FROM users
        WHERE id = :user_id
        FOR UPDATE
    )
    UPDATE users
    SET
        tickets_count = regen.new_count - :n,
        tickets_updated_at = CASE
            WHEN regen.old_count >= :cap THEN now()
            ELSE regen.old_ts + ((regen.new_count - regen.old_count) * regen.effective_interval) * INTERVAL '1 second'
        END
    FROM regen
    WHERE users.id = regen.id AND regen.new_count >= :n
    RETURNING users.tickets_count, users.tickets_updated_at, users.subscription_until
    """
)

_GRANT_SQL = text(
    """
    UPDATE users
    SET
        tickets_count = tickets_count + :amount,
        tickets_updated_at = CASE
            WHEN tickets_count + :amount >= :cap THEN now()
            ELSE tickets_updated_at
        END
    WHERE id = :user_id
    RETURNING tickets_count
    """
)


async def get_balance(session: AsyncSession, user_id: int) -> int:
    """Досчитывает реген и возвращает актуальный баланс (n=0 — ничего не списывает).

    Не коммитит сама — вызывающий код обязан сделать `session.commit()` (см. CLAUDE.md,
    "Границы транзакций": commit — на уровне логической операции целиком, а не в каждой
    отдельной функции, иначе составные операции вроде крутки перестанут быть атомарными)."""
    result = await session.execute(
        _REGEN_AND_SPEND_SQL,
        {
            "cap": TICKET_NATURAL_CAP,
            "interval_normal": TICKET_REGEN_INTERVAL_SECONDS,
            "interval_sub": TICKET_REGEN_INTERVAL_SECONDS_SUBSCRIBED,
            "user_id": user_id,
            "n": 0,
        },
    )
    return result.scalar_one()


async def spend(session: AsyncSession, user_id: int, amount: int) -> int | None:
    """Атомарно списывает `amount` тикетов (после актуализации регена). None — если не хватает.
    Не коммитит — см. get_balance."""
    result = await session.execute(
        _REGEN_AND_SPEND_SQL,
        {
            "cap": TICKET_NATURAL_CAP,
            "interval_normal": TICKET_REGEN_INTERVAL_SECONDS,
            "interval_sub": TICKET_REGEN_INTERVAL_SECONDS_SUBSCRIBED,
            "user_id": user_id,
            "n": amount,
        },
    )
    return result.scalar_one_or_none()


async def grant(session: AsyncSession, user_id: int, amount: int) -> int:
    """Начисляет тикеты сверх капа (магазин за коины/пыль, промокоды, админ-выдача).
    Не коммитит — см. get_balance."""
    result = await session.execute(
        _GRANT_SQL,
        {"amount": amount, "cap": TICKET_NATURAL_CAP, "user_id": user_id},
    )
    return result.scalar_one()


@dataclass
class TicketStatus:
    count: int
    # None — баланс на натур. капе или выше (регена ждать нечего, "заполнено")
    seconds_until_next: int | None


async def get_status(session: AsyncSession, user_id: int) -> TicketStatus:
    """Как get_balance, но также говорит, сколько секунд осталось до следующего тикета
    (для профиля/колоды) — регенерация всё равно применяется тем же запросом."""
    result = await session.execute(
        _REGEN_AND_SPEND_SQL,
        {
            "cap": TICKET_NATURAL_CAP,
            "interval_normal": TICKET_REGEN_INTERVAL_SECONDS,
            "interval_sub": TICKET_REGEN_INTERVAL_SECONDS_SUBSCRIBED,
            "user_id": user_id,
            "n": 0,
        },
    )
    count, updated_at, subscription_until = result.one()
    if count >= TICKET_NATURAL_CAP:
        return TicketStatus(count=count, seconds_until_next=None)

    is_subscribed = subscription_until is not None and subscription_until > datetime.now(timezone.utc)
    interval = TICKET_REGEN_INTERVAL_SECONDS_SUBSCRIBED if is_subscribed else TICKET_REGEN_INTERVAL_SECONDS
    next_tick_at = updated_at + timedelta(seconds=interval)
    remaining = int((next_tick_at - datetime.now(timezone.utc)).total_seconds())
    return TicketStatus(count=count, seconds_until_next=max(0, remaining))
