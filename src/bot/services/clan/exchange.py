from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from bot.constant.clan import TRANSACTION_REASON_CLAN_EXCHANGE
from bot.db.models.enums import TransactionCurrency
from bot.db.models.transaction import Transaction
from bot.db.repositories import clan as clan_repo
from bot.db.repositories.user import add_coins, add_dust, spend_coins, spend_dust
from bot.services import ticket as ticket_service


class NotInSameClanError(Exception):
    pass


class NotEnoughCurrencyError(Exception):
    def __init__(self, currency: TransactionCurrency, needed: int) -> None:
        self.currency = currency
        self.needed = needed


async def exchange_currency(
    session: AsyncSession, *, sender_id: int, receiver_id: int, amount: int, currency: TransactionCurrency
) -> None:
    """Перевод пыли/тикетов/коинов между игроками ОДНОГО клана — обобщённая версия прежней
    exchange_dust (см. CLAUDE.md, "Кланы"). Одна логическая операция — списание у
    отправителя и начисление получателю случаются вместе или не случаются вовсе.

    Тикеты — через services/ticket (spend/grant), а не db/repositories/user напрямую: spend
    уже учитывает лениво накопленный реген перед списанием, как и везде в проекте."""
    sender_member = await clan_repo.get_member(session, sender_id)
    receiver_member = await clan_repo.get_member(session, receiver_id)
    if (
        sender_member is None
        or receiver_member is None
        or sender_member.clan_id != receiver_member.clan_id
    ):
        raise NotInSameClanError

    if currency is TransactionCurrency.dust:
        spent_ok = await spend_dust(session, user_id=sender_id, amount=amount)
    elif currency is TransactionCurrency.coins:
        spent_ok = await spend_coins(session, user_id=sender_id, amount=amount)
    elif currency is TransactionCurrency.tickets:
        spent_ok = (await ticket_service.spend(session, sender_id, amount)) is not None
    else:
        raise ValueError(f"unsupported exchange currency: {currency}")

    if not spent_ok:
        raise NotEnoughCurrencyError(currency=currency, needed=amount)

    if currency is TransactionCurrency.dust:
        await add_dust(session, user_id=receiver_id, amount=amount)
    elif currency is TransactionCurrency.coins:
        await add_coins(session, user_id=receiver_id, amount=amount)
    else:
        await ticket_service.grant(session, receiver_id, amount)

    session.add(
        Transaction(user_id=sender_id, currency=currency, amount=-amount, reason=TRANSACTION_REASON_CLAN_EXCHANGE)
    )
    session.add(
        Transaction(user_id=receiver_id, currency=currency, amount=amount, reason=TRANSACTION_REASON_CLAN_EXCHANGE)
    )
    await session.commit()
