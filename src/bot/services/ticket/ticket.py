from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.game import TICKET_NATURAL_CAP, TICKET_REGEN_INTERVAL_SECONDS, TICKET_REGEN_INTERVAL_SECONDS_SUBSCRIBED

# Эффективный кап тикета — не просто TICKET_NATURAL_CAP, а он же + купленные в магазине
# слоты (см. CLAUDE.md, "Магазин: слот капа тикетов"): ticket_cap_permanent_bonus стакается
# всегда, ticket_cap_seasonal_bonus — ТОЛЬКО пока ticket_cap_seasonal_season_id совпадает с
# ID ещё активного сезона (сезон переключается админом, не календарным таймером — тот же
# принцип границы, что у ubp_season). Строка `users` уже читается/блокируется в этой же CTE,
# поэтому подзапрос к `seasons` не требует отдельного похода в БД сверху. Выражение
# продублировано несколько раз внутри одного SELECT — Postgres не даёт сослаться на алиас
# соседней колонки внутри того же SELECT (та же причина, по которой effective_interval ниже
# тоже продублирован дважды). Публичный (не `_`-приватный) — переиспользуется в
# services/notify (уведомление "тикеты заполнены") и services/admin/mass_grant (массовая
# выдача тикетов), у которых тот же анти-эксплойт freeze-паттерн на СВОИХ raw SQL — те
# запросы обязаны сравнивать с тем же эффективным капом, иначе игрок с купленным слотом
# получит уведомление/заморозку регена раньше настоящего личного потолка.
CAP_SQL_EXPR = (
    "(:cap_base + ticket_cap_permanent_bonus + CASE "
    "WHEN ticket_cap_seasonal_season_id = (SELECT id FROM seasons WHERE is_active = true) "
    "THEN ticket_cap_seasonal_bonus ELSE 0 END)"
)

# Один атомарный запрос: досчитывает лениво накопленный реген (с "заморозкой" таймера,
# пока баланс >= капа — см. CLAUDE.md, "Модель тикетов", про анти-эксплойт) и сразу же
# списывает :n (может быть 0 — тогда это просто "актуализировать и вернуть баланс").
# FOR UPDATE — блокирует строку от параллельного двойного клика на то же действие.
# Интервал регена — :interval_sub, пока подписка активна (subscription_until > now()),
# иначе :interval_normal (см. CLAUDE.md, "Подписка") — выражение продублировано дважды
# (для new_count и для сдвига tickets_updated_at), т.к. Postgres не даёт сослаться на
# алиас соседней колонки внутри того же SELECT. RETURNING отдаёт regen.cap ПОСЛЕДНИМ
# столбцом — get_balance/spend его игнорируют (берут только первую колонку), get_status
# читает его явно, чтобы не дублировать этот же запрос ещё раз только ради капа.
_REGEN_AND_SPEND_SQL = text(
    f"""
    WITH regen AS (
        SELECT
            id,
            tickets_count AS old_count,
            tickets_updated_at AS old_ts,
            CASE WHEN subscription_until > now() THEN CAST(:interval_sub AS INTEGER) ELSE CAST(:interval_normal AS INTEGER) END AS effective_interval,
            {CAP_SQL_EXPR} AS cap,
            CASE
                WHEN tickets_count >= {CAP_SQL_EXPR} THEN tickets_count
                ELSE LEAST(
                    {CAP_SQL_EXPR},
                    tickets_count + FLOOR(
                        EXTRACT(EPOCH FROM (now() - tickets_updated_at)) /
                        (CASE WHEN subscription_until > now() THEN CAST(:interval_sub AS INTEGER) ELSE CAST(:interval_normal AS INTEGER) END)
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
            WHEN regen.old_count >= regen.cap THEN now()
            ELSE regen.old_ts + ((regen.new_count - regen.old_count) * regen.effective_interval) * INTERVAL '1 second'
        END
    FROM regen
    WHERE users.id = regen.id AND regen.new_count >= :n
    RETURNING users.tickets_count, users.tickets_updated_at, users.subscription_until, regen.cap
    """
)

_GRANT_SQL = text(
    f"""
    UPDATE users
    SET
        tickets_count = GREATEST(tickets_count + :amount, 0),
        tickets_updated_at = CASE
            WHEN tickets_count + :amount >= {CAP_SQL_EXPR} THEN now()
            ELSE tickets_updated_at
        END
    WHERE id = :user_id
    RETURNING tickets_count
    """
)


def _params(user_id: int, n: int) -> dict[str, object]:
    return {
        "cap_base": TICKET_NATURAL_CAP,
        "interval_normal": TICKET_REGEN_INTERVAL_SECONDS,
        "interval_sub": TICKET_REGEN_INTERVAL_SECONDS_SUBSCRIBED,
        "user_id": user_id,
        "n": n,
    }


async def get_balance(session: AsyncSession, user_id: int) -> int:
    """Досчитывает реген и возвращает актуальный баланс (n=0 — ничего не списывает).

    Не коммитит сама — вызывающий код обязан сделать `session.commit()` (см. CLAUDE.md,
    "Границы транзакций": commit — на уровне логической операции целиком, а не в каждой
    отдельной функции, иначе составные операции вроде крутки перестанут быть атомарными)."""
    result = await session.execute(_REGEN_AND_SPEND_SQL, _params(user_id, 0))
    return result.scalar_one()


async def spend(session: AsyncSession, user_id: int, amount: int) -> int | None:
    """Атомарно списывает `amount` тикетов (после актуализации регена). None — если не хватает.
    Не коммитит — см. get_balance."""
    result = await session.execute(_REGEN_AND_SPEND_SQL, _params(user_id, amount))
    return result.scalar_one_or_none()


async def grant(session: AsyncSession, user_id: int, amount: int) -> int:
    """Начисляет тикеты сверх капа (магазин за коины/пыль, промокоды, админ-выдача).
    `amount` может быть отрицательным (промокод-штраф, см. CLAUDE.md, "Промокоды") — баланс
    клампится к 0 (GREATEST в _GRANT_SQL), не уходит в минус. Не коммитит — см. get_balance."""
    result = await session.execute(
        _GRANT_SQL,
        {"amount": amount, "cap_base": TICKET_NATURAL_CAP, "user_id": user_id},
    )
    return result.scalar_one()


@dataclass
class TicketStatus:
    count: int
    # None — баланс на натур. капе или выше (регена ждать нечего, "заполнено")
    seconds_until_next: int | None
    cap: int


async def get_status(session: AsyncSession, user_id: int) -> TicketStatus:
    """Как get_balance, но также говорит, сколько секунд осталось до следующего тикета
    (для профиля/колоды) — регенерация всё равно применяется тем же запросом. `cap` —
    эффективный потолок ЭТОГО игрока (TICKET_NATURAL_CAP + купленные слоты), не глобальная
    константа — экран должен показывать то, что реально применяется."""
    result = await session.execute(_REGEN_AND_SPEND_SQL, _params(user_id, 0))
    count, updated_at, subscription_until, cap = result.one()
    if count >= cap:
        return TicketStatus(count=count, seconds_until_next=None, cap=cap)

    is_subscribed = subscription_until is not None and subscription_until > datetime.now(timezone.utc)
    interval = TICKET_REGEN_INTERVAL_SECONDS_SUBSCRIBED if is_subscribed else TICKET_REGEN_INTERVAL_SECONDS
    next_tick_at = updated_at + timedelta(seconds=interval)
    remaining = int((next_tick_at - datetime.now(timezone.utc)).total_seconds())
    return TicketStatus(count=count, seconds_until_next=max(0, remaining), cap=cap)
