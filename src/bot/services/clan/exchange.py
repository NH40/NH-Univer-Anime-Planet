from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from bot.constant.clan import TRANSACTION_REASON_CLAN_EXCHANGE
from bot.db.models.enums import TransactionCurrency
from bot.db.models.transaction import Transaction
from bot.db.repositories import clan as clan_repo
from bot.db.repositories.user import add_dust, spend_dust


class NotInSameClanError(Exception):
    pass


class NotEnoughDustError(Exception):
    def __init__(self, needed: int) -> None:
        self.needed = needed


async def exchange_dust(session: AsyncSession, *, sender_id: int, receiver_id: int, amount: int) -> None:
    """Перевод пыли между игроками ОДНОГО клана. Одна логическая операция — списание у
    отправителя и начисление получателю случаются вместе или не случаются вовсе."""
    sender_member = await clan_repo.get_member(session, sender_id)
    receiver_member = await clan_repo.get_member(session, receiver_id)
    if (
        sender_member is None
        or receiver_member is None
        or sender_member.clan_id != receiver_member.clan_id
    ):
        raise NotInSameClanError

    ok = await spend_dust(session, user_id=sender_id, amount=amount)
    if not ok:
        raise NotEnoughDustError(needed=amount)

    await add_dust(session, user_id=receiver_id, amount=amount)
    session.add(
        Transaction(
            user_id=sender_id, currency=TransactionCurrency.dust, amount=-amount, reason=TRANSACTION_REASON_CLAN_EXCHANGE
        )
    )
    session.add(
        Transaction(
            user_id=receiver_id, currency=TransactionCurrency.dust, amount=amount, reason=TRANSACTION_REASON_CLAN_EXCHANGE
        )
    )
    await session.commit()
