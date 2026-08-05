from __future__ import annotations

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.enums import TransactionCurrency
from bot.db.models.transaction import Transaction
from bot.db.models.user import User


async def award_ubp(
    session: AsyncSession,
    *,
    user_id: int,
    amount: int,
    reason: str,
) -> int:
    """Единая точка изменения ubp_season: атомарный UPDATE в Postgres (источник правды) +
    запись в аудит-лог `transactions`. `amount` может быть отрицательным. ubp_total здесь
    не трогаем — он пополняется только при смене сезона (см. TODO, Этап 10).

    Не коммитит и не трогает Redis-лидерборд — это намеренно (см. CLAUDE.md, "Границы
    транзакций"): если вызывающий код композирует несколько шагов в одну логическую
    операцию (крутка, слияние) и один из последующих шагов упадёт, вся транзакция должна
    откатиться целиком. Redis не участвует в транзакции Postgres, поэтому синхронизацию
    лидерборда (`cache.leaderboard.sync_score`) нужно делать ПОСЛЕ успешного `commit()`,
    иначе при откате Redis разъедется с Postgres."""
    result = await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(ubp_season=User.ubp_season + amount)
        .returning(User.ubp_season)
    )
    new_score = result.scalar_one()
    session.add(
        Transaction(
            user_id=user_id,
            currency=TransactionCurrency.ubp_season,
            amount=amount,
            reason=reason,
        )
    )
    return new_score
