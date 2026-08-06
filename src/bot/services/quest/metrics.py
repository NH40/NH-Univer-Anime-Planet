from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.quest import QUEST_METRICS
from bot.db.models.transaction import Transaction


async def resolve_progress(session: AsyncSession, *, user_id: int, metric_key: str, since: datetime) -> int:
    """Живая агрегация прогресса задания прямо по журналу `transactions` (использует
    существующий индекс `ix_transactions_user_created`) — без отдельного счётчика
    прогресса на задание, тот же принцип "живая агрегация", что у UBP клана/прогресса
    коллекции (см. CLAUDE.md, правило 3)."""
    metric = QUEST_METRICS[metric_key]
    conditions = [
        Transaction.user_id == user_id,
        Transaction.created_at >= since,
        Transaction.reason.in_(metric.reasons),
    ]
    if metric.currency is not None:
        conditions.append(Transaction.currency == metric.currency)

    if metric.mode == "count":
        stmt = select(func.count()).select_from(Transaction).where(*conditions)
    elif metric.mode == "sum_positive":
        conditions.append(Transaction.amount > 0)
        stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).where(*conditions)
    else:  # sum_abs_negative
        conditions.append(Transaction.amount < 0)
        stmt = select(func.coalesce(func.sum(-Transaction.amount), 0)).where(*conditions)

    result = await session.execute(stmt)
    return int(result.scalar_one())
