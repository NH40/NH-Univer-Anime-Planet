from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.game import (
    BATTLE_PASS_EXTEND_DURATION_DAYS,
    BATTLE_PASS_FIRST_DURATION_DAYS,
    BATTLE_PASS_PRICE_COINS,
    SHOP_COIN_TICKET_PRICE,
    SHOP_TICKET_PRICE_DUST,
    SUBSCRIPTION_DURATION_DAYS,
    SUBSCRIPTION_PRICE_COINS,
)
from bot.constant.shop import (
    TRANSACTION_REASON_BATTLE_PASS,
    TRANSACTION_REASON_SHOP_COIN_TICKET,
    TRANSACTION_REASON_SHOP_TICKET,
    TRANSACTION_REASON_SUBSCRIPTION,
)
from bot.db.models.enums import TransactionCurrency
from bot.db.models.transaction import Transaction
from bot.db.repositories import battle_pass as pass_repo
from bot.db.repositories import season as season_repo
from bot.db.repositories.user import extend_premium_pass, extend_subscription, spend_coins, spend_dust
from bot.services import ticket


class NotEnoughDustError(Exception):
    def __init__(self, needed: int) -> None:
        self.needed = needed


class NotEnoughCoinsError(Exception):
    def __init__(self, needed: int) -> None:
        self.needed = needed


async def buy_tickets(session: AsyncSession, *, user_id: int, quantity: int) -> int:
    """Покупка `quantity` тикетов за пыль (SHOP_TICKET_PRICE_DUST за штуку). Одна логическая
    операция — списание пыли и начисление тикетов случаются вместе или не случаются вовсе
    (см. CLAUDE.md, правило 10). Возвращает потраченную пыль."""
    cost = quantity * SHOP_TICKET_PRICE_DUST

    ok = await spend_dust(session, user_id=user_id, amount=cost)
    if not ok:
        raise NotEnoughDustError(needed=cost)

    await ticket.grant(session, user_id, quantity)
    session.add(
        Transaction(
            user_id=user_id,
            currency=TransactionCurrency.dust,
            amount=-cost,
            reason=TRANSACTION_REASON_SHOP_TICKET,
        )
    )

    await session.commit()
    return cost


async def buy_tickets_with_coins(session: AsyncSession, *, user_id: int, quantity: int) -> int:
    """Покупка `quantity` тикетов за коины (SHOP_COIN_TICKET_PRICE за штуку). Возвращает
    потраченные коины."""
    cost = quantity * SHOP_COIN_TICKET_PRICE

    ok = await spend_coins(session, user_id=user_id, amount=cost)
    if not ok:
        raise NotEnoughCoinsError(needed=cost)

    await ticket.grant(session, user_id, quantity)
    session.add(
        Transaction(
            user_id=user_id,
            currency=TransactionCurrency.coins,
            amount=-cost,
            reason=TRANSACTION_REASON_SHOP_COIN_TICKET,
        )
    )

    await session.commit()
    return cost


async def buy_subscription(session: AsyncSession, *, user_id: int) -> datetime:
    """Покупка/продление подписки: SUBSCRIPTION_PRICE_COINS -> +SUBSCRIPTION_DURATION_DAYS
    к текущему истечению (стакается, см. CLAUDE.md). Возвращает новую дату истечения."""
    ok = await spend_coins(session, user_id=user_id, amount=SUBSCRIPTION_PRICE_COINS)
    if not ok:
        raise NotEnoughCoinsError(needed=SUBSCRIPTION_PRICE_COINS)

    new_until = await extend_subscription(session, user_id=user_id, days=SUBSCRIPTION_DURATION_DAYS)
    session.add(
        Transaction(
            user_id=user_id,
            currency=TransactionCurrency.coins,
            amount=-SUBSCRIPTION_PRICE_COINS,
            reason=TRANSACTION_REASON_SUBSCRIPTION,
        )
    )

    await session.commit()
    return new_until


async def buy_premium_pass(session: AsyncSession, *, user_id: int) -> datetime:
    """Покупка/продление Premium Battle Pass: BATTLE_PASS_PRICE_COINS -> +30 дней (первая
    покупка, нет активного) или +20 дней (пока пасс ещё активен), см. CLAUDE.md. Возвращает
    новую дату истечения `User.premium_pass_until` (это отдельный от сезона таймер).

    Дополнительно — если сейчас есть активный сезон — разово и НАВСЕГДА (до конца этого
    сезона) открывает премиум-ветку сезонного пасса (`services/battle_pass`), независимо от
    того, истечёт ли `premium_pass_until` раньше конца сезона (см. `db/models/battle_pass.py`,
    подтверждено пользователем 2026-08-05). Если активного сезона нет — открывать премиум-ветку
    нечему, только продление `premium_pass_until` всё равно происходит."""
    ok = await spend_coins(session, user_id=user_id, amount=BATTLE_PASS_PRICE_COINS)
    if not ok:
        raise NotEnoughCoinsError(needed=BATTLE_PASS_PRICE_COINS)

    new_until = await extend_premium_pass(
        session,
        user_id=user_id,
        first_days=BATTLE_PASS_FIRST_DURATION_DAYS,
        extend_days=BATTLE_PASS_EXTEND_DURATION_DAYS,
    )
    session.add(
        Transaction(
            user_id=user_id,
            currency=TransactionCurrency.coins,
            amount=-BATTLE_PASS_PRICE_COINS,
            reason=TRANSACTION_REASON_BATTLE_PASS,
        )
    )

    season = await season_repo.get_active(session)
    if season is not None:
        await pass_repo.set_premium(session, user_id=user_id, season_id=season.id)

    await session.commit()
    return new_until
