from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.enums import TransactionCurrency
from bot.db.models.transaction import Transaction
from bot.db.models.user import User
from bot.db.repositories import universe_ubp as universe_ubp_repo


@dataclass
class UbpAward:
    ubp_season: int  # новый общий User.ubp_season после начисления
    universe_ubp_season: int | None  # новый UserUniverseUbp.ubp_season, если universe_code передан


async def award_ubp(
    session: AsyncSession,
    *,
    user_id: int,
    amount: int,
    reason: str,
    universe_code: str | None = None,
) -> UbpAward:
    """Единая точка изменения ubp_season: атомарный UPDATE в Postgres (источник правды) +
    запись в аудит-лог `transactions`. `amount` может быть отрицательным. ubp_total здесь
    не трогаем — он пополняется только при смене сезона (см. services/season).

    `universe_code` (см. CLAUDE.md, "Топ по вселенной") — если передан, ТЕМ ЖЕ вызовом
    дополнительно начисляет `UserUniverseUbp.ubp_season` этой вселенной (крутка/слияние
    всегда знают вселенную карты, за которую начисляется UBP). Общий счётчик игрока при
    этом не заменяется — оба растут параллельно из одного события. Небесные/божественные
    карты (см. services/celestial) начисляют UBP через этот же путь, с universe_code своей
    домашней вселенной — им не нужна отдельная логика подсчёта в топах.

    Не коммитит и не трогает Redis-лидерборды — это намеренно (см. CLAUDE.md, "Границы
    транзакций"): если вызывающий код композирует несколько шагов в одну логическую
    операцию (крутка, слияние) и один из последующих шагов упадёт, вся транзакция должна
    откатиться целиком. Redis не участвует в транзакции Postgres, поэтому синхронизацию
    лидербордов (`cache.leaderboard`/`cache.universe_leaderboard`) нужно делать ПОСЛЕ
    успешного `commit()`, иначе при откате Redis разъедется с Postgres."""
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

    universe_score = None
    if universe_code is not None:
        universe_score = await universe_ubp_repo.award(
            session, user_id=user_id, universe_code=universe_code, amount=amount
        )

    return UbpAward(ubp_season=new_score, universe_ubp_season=universe_score)
