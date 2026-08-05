from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.game import TICKET_NATURAL_CAP
from bot.constant.admin import TRANSACTION_REASON_ADMIN_MASS_GRANT

# Массовая выдача — это UPDATE + INSERT...SELECT ОДНИМ запросом на ВСЕХ игроков разом
# (writable CTE), не Python-цикл по 30k строк (см. CLAUDE.md, правило 3). Аудит-лог
# (transactions) заполняется из того же набора обновлённых строк той же командой.
_MASS_GRANT_DUST_SQL = text(
    """
    WITH updated AS (
        UPDATE users SET dust = dust + :amount RETURNING id
    )
    INSERT INTO transactions (user_id, currency, amount, reason, admin_id)
    SELECT id, 'dust', :amount, :reason, :admin_id FROM updated
    """
)

_MASS_GRANT_COINS_SQL = text(
    """
    WITH updated AS (
        UPDATE users SET coins = coins + :amount RETURNING id
    )
    INSERT INTO transactions (user_id, currency, amount, reason, admin_id)
    SELECT id, 'coins', :amount, :reason, :admin_id FROM updated
    """
)

_MASS_GRANT_TICKETS_SQL = text(
    """
    WITH updated AS (
        UPDATE users
        SET tickets_count = tickets_count + :amount,
            tickets_updated_at = CASE
                WHEN tickets_count + :amount >= :cap THEN now()
                ELSE tickets_updated_at
            END
        RETURNING id
    )
    INSERT INTO transactions (user_id, currency, amount, reason, admin_id)
    SELECT id, 'tickets', :amount, :reason, :admin_id FROM updated
    """
)


async def mass_grant_dust(session: AsyncSession, *, amount: int, admin_id: int) -> int:
    result = await session.execute(
        _MASS_GRANT_DUST_SQL, {"amount": amount, "reason": TRANSACTION_REASON_ADMIN_MASS_GRANT, "admin_id": admin_id}
    )
    await session.commit()
    return result.rowcount


async def mass_grant_coins(session: AsyncSession, *, amount: int, admin_id: int) -> int:
    result = await session.execute(
        _MASS_GRANT_COINS_SQL, {"amount": amount, "reason": TRANSACTION_REASON_ADMIN_MASS_GRANT, "admin_id": admin_id}
    )
    await session.commit()
    return result.rowcount


async def mass_grant_tickets(session: AsyncSession, *, amount: int, admin_id: int) -> int:
    result = await session.execute(
        _MASS_GRANT_TICKETS_SQL,
        {
            "amount": amount,
            "cap": TICKET_NATURAL_CAP,
            "reason": TRANSACTION_REASON_ADMIN_MASS_GRANT,
            "admin_id": admin_id,
        },
    )
    await session.commit()
    return result.rowcount
