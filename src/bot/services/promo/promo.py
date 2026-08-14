from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from bot.constant.admin import TRANSACTION_REASON_PROMO
from bot.db.models.enums import PromoCodeType, TransactionCurrency
from bot.db.models.transaction import Transaction
from bot.db.repositories import promocode as promo_repo
from bot.db.repositories.user import apply_coins_delta, apply_dust_delta
from bot.services import ticket


class PromoTakenError(Exception):
    pass


class PromoNotFoundError(Exception):
    pass


class PromoExpiredError(Exception):
    pass


class PromoNotAllowedError(Exception):
    pass


class PromoUsesExhaustedError(Exception):
    pass


class PromoAlreadyRedeemedError(Exception):
    pass


@dataclass
class PromoStatus:
    code: str
    is_active: bool
    dust: int
    coins: int
    tickets: int
    max_uses: int | None
    used_count: int


async def list_status(session: AsyncSession, *, limit: int = 20) -> list[PromoStatus]:
    """Последние выпущенные промокоды со статусом (активен/нет) — экран /admin -> Промокоды
    (см. CLAUDE.md, "Промокоды: список существующих"). Активен = не истёк по времени И
    (лимита активаций нет, либо он ещё не исчерпан) — та же логика, что проверяет redeem()
    при активации, просто без похода в БД за инкрементом."""
    codes = await promo_repo.list_recent(session, limit=limit)
    now = datetime.now(timezone.utc)
    statuses = []
    for promo in codes:
        expired = promo.expires_at is not None and promo.expires_at <= now
        exhausted = promo.max_uses is not None and promo.used_count >= promo.max_uses
        reward = promo.reward or {}
        statuses.append(
            PromoStatus(
                code=promo.code,
                is_active=not expired and not exhausted,
                dust=int(reward.get("dust", 0)),
                coins=int(reward.get("coins", 0)),
                tickets=int(reward.get("tickets", 0)),
                max_uses=promo.max_uses,
                used_count=promo.used_count,
            )
        )
    return statuses


async def create_promo(
    session: AsyncSession,
    *,
    code: str,
    type_: PromoCodeType,
    max_uses: int | None,
    expires_at: datetime | None,
    allowed_usernames: list[str] | None,
    reward: dict[str, int],
) -> None:
    """`reward` — {"tickets"|"coins"|"dust": количество}, только заданные ключи (не всегда
    все три, см. handlers/admin/promo.py — одна строка вида "coins:1000 tickets:5" вместо
    прежних фиксированных 3 чисел). Количество может быть отрицательным — промокод-штраф
    (см. CLAUDE.md, "Промокоды"), клампится к 0 при активации, не здесь."""
    ok = await promo_repo.create(
        session,
        code=code,
        type_=type_,
        max_uses=max_uses,
        expires_at=expires_at,
        allowed_usernames=allowed_usernames,
        reward=reward,
    )
    if not ok:
        raise PromoTakenError
    await session.commit()


async def redeem(session: AsyncSession, *, code: str, user_id: int, username: str | None) -> dict:
    """Атомарно проверяет все условия и активирует промокод, начисляя награду. Одна
    логическая операция — один commit в конце. `used_count` инкрементируется атомарным
    UPDATE с условием прямо в WHERE (см. db/repositories/promocode) — гонка на лимите
    активаций исключена без отдельного Redis-лока."""
    promo = await promo_repo.get_by_code(session, code)
    if promo is None:
        raise PromoNotFoundError

    if promo.expires_at is not None and promo.expires_at <= datetime.now(timezone.utc):
        raise PromoExpiredError

    if promo.allowed_usernames is not None:
        allowed = {u.lower() for u in promo.allowed_usernames}
        if username is None or username.lower() not in allowed:
            raise PromoNotAllowedError

    redeemed = await promo_repo.create_redemption(session, code=code, user_id=user_id)
    if not redeemed:
        raise PromoAlreadyRedeemedError

    incremented = await promo_repo.increment_used_count(session, code=code)
    if not incremented:
        # Гонка: лимит активаций исчерпан между чтением промокода выше и этим инкрементом —
        # откатываем только что вставленный redemption, ничего не начисляем.
        await session.rollback()
        raise PromoUsesExhaustedError

    reward = promo.reward or {}
    dust = int(reward.get("dust", 0))
    coins = int(reward.get("coins", 0))
    tickets = int(reward.get("tickets", 0))

    # apply_*_delta/ticket.grant — оба знака (штрафной промокод даёт отрицательное
    # количество, см. CLAUDE.md, "Промокоды"), баланс клампится к 0, не уходит в минус.
    if dust:
        await apply_dust_delta(session, user_id=user_id, delta=dust)
        session.add(Transaction(user_id=user_id, currency=TransactionCurrency.dust, amount=dust, reason=TRANSACTION_REASON_PROMO))
    if coins:
        await apply_coins_delta(session, user_id=user_id, delta=coins)
        session.add(Transaction(user_id=user_id, currency=TransactionCurrency.coins, amount=coins, reason=TRANSACTION_REASON_PROMO))
    if tickets:
        await ticket.grant(session, user_id, tickets)
        session.add(Transaction(user_id=user_id, currency=TransactionCurrency.tickets, amount=tickets, reason=TRANSACTION_REASON_PROMO))

    await session.commit()
    return {"dust": dust, "coins": coins, "tickets": tickets}
