from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.game import (
    BATTLE_PASS_PRICE_COINS,
    SHOP_COIN_TICKET_PRICE,
    SHOP_TICKET_PRICE_DUST,
    SUBSCRIPTION_DURATION_DAYS,
    SUBSCRIPTION_PRICE_COINS,
    TICKET_CAP_SLOT_BONUS,
    TICKET_CAP_SLOT_PRICE_PERMANENT_COINS,
    TICKET_CAP_SLOT_PRICE_SEASONAL_COINS,
)
from bot.constant.shop import (
    TICKET_CAP_KIND_SEASONAL,
    TRANSACTION_REASON_BATTLE_PASS,
    TRANSACTION_REASON_SHOP_COIN_TICKET,
    TRANSACTION_REASON_SHOP_TICKET,
    TRANSACTION_REASON_SUBSCRIPTION,
    TRANSACTION_REASON_TICKET_CAP_PERMANENT,
    TRANSACTION_REASON_TICKET_CAP_SEASONAL,
)
from bot.db.models.enums import TransactionCurrency
from bot.db.models.transaction import Transaction
from bot.db.repositories import battle_pass as pass_repo
from bot.db.repositories import season as season_repo
from bot.db.repositories.user import (
    extend_subscription,
    grant_ticket_cap_permanent_bonus,
    grant_ticket_cap_seasonal_bonus,
    spend_coins,
    spend_dust,
)
from bot.services import ticket


class NotEnoughDustError(Exception):
    def __init__(self, needed: int) -> None:
        self.needed = needed


class NotEnoughCoinsError(Exception):
    def __init__(self, needed: int) -> None:
        self.needed = needed


class NoActiveSeasonError(Exception):
    pass


class AlreadyPremiumError(Exception):
    """Премиум-ветка Battle Pass этого сезона уже открыта — повторная покупка не даёт
    ничего нового (см. CLAUDE.md, "Сезонный пасс": разовая разблокировка на сезон)."""


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


async def buy_premium_pass(session: AsyncSession, *, user_id: int) -> None:
    """Покупка Premium Battle Pass: BATTLE_PASS_PRICE_COINS -> премиум-ветка сезонного пасса
    открыта НАВСЕГДА до конца ТЕКУЩЕГО сезона (см. CLAUDE.md, "Сезонный пасс") — разовая
    покупка, не подписка на дни. Требует активный сезон (иначе покупать нечего) и что
    премиум ещё не открыт в этом сезоне (повторная покупка ничего бы не добавила)."""
    season = await season_repo.get_active(session)
    if season is None:
        raise NoActiveSeasonError

    row = await pass_repo.get_or_create(session, user_id=user_id, season_id=season.id)
    if row.is_premium:
        raise AlreadyPremiumError

    ok = await spend_coins(session, user_id=user_id, amount=BATTLE_PASS_PRICE_COINS)
    if not ok:
        raise NotEnoughCoinsError(needed=BATTLE_PASS_PRICE_COINS)

    await pass_repo.set_premium(session, user_id=user_id, season_id=season.id)
    session.add(
        Transaction(
            user_id=user_id,
            currency=TransactionCurrency.coins,
            amount=-BATTLE_PASS_PRICE_COINS,
            reason=TRANSACTION_REASON_BATTLE_PASS,
        )
    )

    await session.commit()


async def buy_ticket_cap_with_coins(session: AsyncSession, *, user_id: int, kind: str, quantity: int) -> tuple[int, int]:
    """Покупка `quantity` слотов капа тикетов за коины (изменено 2026-08-17 — раньше слот
    продавался за рубли через YooKassa-инвойс, см. CLAUDE.md). `kind` —
    TICKET_CAP_KIND_SEASONAL/PERMANENT. Возвращает (потраченные коины, новое значение
    бонуса)."""
    is_seasonal = kind == TICKET_CAP_KIND_SEASONAL
    price = TICKET_CAP_SLOT_PRICE_SEASONAL_COINS if is_seasonal else TICKET_CAP_SLOT_PRICE_PERMANENT_COINS
    cost = quantity * price
    bonus = quantity * TICKET_CAP_SLOT_BONUS

    season = await season_repo.get_active(session) if is_seasonal else None
    if is_seasonal and season is None:
        raise NoActiveSeasonError

    ok = await spend_coins(session, user_id=user_id, amount=cost)
    if not ok:
        raise NotEnoughCoinsError(needed=cost)

    if is_seasonal:
        new_bonus = await grant_ticket_cap_seasonal_bonus(session, user_id=user_id, season_id=season.id, amount=bonus)
        reason = TRANSACTION_REASON_TICKET_CAP_SEASONAL
    else:
        new_bonus = await grant_ticket_cap_permanent_bonus(session, user_id=user_id, amount=bonus)
        reason = TRANSACTION_REASON_TICKET_CAP_PERMANENT

    session.add(
        Transaction(user_id=user_id, currency=TransactionCurrency.coins, amount=-cost, reason=reason)
    )

    await session.commit()
    return cost, new_bonus
