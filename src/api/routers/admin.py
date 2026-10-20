"""Админ-панель Mini App (2026-10-20) — тот же набор, что `/admin` в боте, плюс то, чего в боте
нет: дашборд с графиками за 14 дней, поиск игроков по имени, лог транзакций игрока, правка
валют в обе стороны, личное сообщение игроку, список платежей. Каждая мутация — вызов того же
сервиса/репозитория бота, что и хендлер `/admin`, без своей игровой логики (см. CLAUDE.md,
"Mini App"). Доступ — `services.admin.is_admin` на каждый запрос; управление админами — только
супер-админы из `ADMIN_IDS`, как в боте."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user_id
from api.db import get_session, session_factory
from api.deps import get_redis
from bot.config.settings import get_settings
from bot.db.models import Card, Transaction, User
from bot.db.models.enums import PromoCodeType, TransactionCurrency

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])
_settings = get_settings()
_tasks: set[asyncio.Task] = set()  # держим ссылки на фоновые рассылки (см. CLAUDE.md, "Рассылка")


def _bot() -> Bot:
    return Bot(token=_settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


def bad(msg: str) -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, msg)


async def require_admin(user_id: int = Depends(get_current_user_id), session: AsyncSession = Depends(get_session)) -> int:
    from bot.services.admin import is_admin

    if not await is_admin(session, user_id, _settings):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Нет доступа")
    return user_id


def require_super(admin_id: int = Depends(require_admin)) -> int:
    from bot.services.admin import is_config_admin

    if not is_config_admin(admin_id, _settings):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Только для супер-админов")
    return admin_id


def _spawn(coro) -> None:
    task = asyncio.create_task(coro)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def _target(session: AsyncSession, user_id: int) -> User:
    from bot.db.repositories.user import get_by_id

    user = await get_by_id(session, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Игрок не найден")
    return user


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------- дашборд

@router.get("/dashboard")
async def dashboard(admin_id: int = Depends(require_admin), session: AsyncSession = Depends(get_session), redis: Redis = Depends(get_redis)) -> dict:
    from bot.constant.gacha import TRANSACTION_REASON_ROLL
    from bot.db.repositories.season import get_active
    from bot.services.admin import get_tech_mode
    from bot.services.admin.stats import get_stats

    st = await get_stats(session)
    since = datetime.now(timezone.utc) - timedelta(days=13)
    day0 = since.date()

    async def series(sql: str, **params) -> list[dict]:
        rows = dict((await session.execute(text(sql), {"since": day0, **params})).all())
        return [{"day": (day0 + timedelta(days=i)).isoformat(), "value": int(rows.get(day0 + timedelta(days=i), 0))} for i in range(14)]

    regs = await series("SELECT created_at::date d, COUNT(*) FROM users WHERE created_at::date >= :since GROUP BY d")
    active = await series("SELECT last_active_at::date d, COUNT(*) FROM users WHERE last_active_at::date >= :since GROUP BY d")
    rolls = await series(
        "SELECT created_at::date d, COUNT(*) FROM transactions WHERE reason = :r AND created_at::date >= :since GROUP BY d",
        r=TRANSACTION_REASON_ROLL,
    )
    revenue = await series(
        "SELECT created_at::date d, COALESCE(SUM(amount_rub), 0) FROM payments WHERE status = 'succeeded' AND created_at::date >= :since GROUP BY d"
    )
    eco = (await session.execute(text(
        "SELECT COALESCE(SUM(dust),0), COALESCE(SUM(coins),0), COALESCE(SUM(tickets_count),0), COALESCE(SUM(total_rolls),0), "
        "COUNT(*) FILTER (WHERE subscription_until > now()), COUNT(*) FILTER (WHERE is_banned), "
        "COUNT(*) FILTER (WHERE created_at > now() - interval '1 day') FROM users"
    ))).one()
    cards = (await session.execute(text("SELECT COALESCE(SUM(quantity),0) FROM user_cards"))).scalar_one()
    recent = (await session.execute(
        select(User.id, User.display_name, User.username, User.created_at, User.ubp_season).order_by(User.created_at.desc()).limit(10)
    )).all()
    season = await get_active(session)
    return {
        "users": st.total_users, "online": st.online_users, "new_24h": int(eco[6]),
        "payments_count": st.payments_count, "payments_rub": st.payments_rub,
        "server": {"cpu": st.server.cpu_percent, "ram": st.server.ram_percent, "ram_used": st.server.ram_used_mb,
                   "ram_total": st.server.ram_total_mb, "disk": st.server.disk_percent},
        "economy": {"dust": int(eco[0]), "coins": int(eco[1]), "tickets": int(eco[2]), "rolls": int(eco[3]),
                    "subscribers": int(eco[4]), "banned": int(eco[5]), "cards": int(cards)},
        "charts": {"registrations": regs, "active": active, "rolls": rolls, "revenue": revenue},
        "recent": [{"id": i, "name": n or (f"@{u}" if u else str(i)), "created_at": _iso(c), "ubp": s} for i, n, u, c, s in recent],
        "season": {"version": season.version, "started_at": _iso(season.started_at)} if season else None,
        "tech_mode": await get_tech_mode(redis),
        "is_super": admin_id in _settings.admin_ids,
    }


class ToggleIn(BaseModel):
    enabled: bool


@router.post("/tech-mode")
async def tech_mode(body: ToggleIn, _: int = Depends(require_admin), redis: Redis = Depends(get_redis)) -> dict:
    from bot.services.admin import set_tech_mode

    await set_tech_mode(redis, body.enabled)
    return {"message": "Техрежим включён." if body.enabled else "Техрежим выключен."}


# ---------------------------------------------------------------- игроки

@router.get("/players")
async def players(q: str = "", offset: int = 0, _: int = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> dict:
    stmt = select(User.id, User.display_name, User.username, User.ubp_season, User.is_banned, User.is_admin, User.last_active_at)
    raw = q.strip().lstrip("@")
    if raw:
        conds = [User.username.ilike(f"%{raw}%"), User.display_name.ilike(f"%{raw}%")]
        if raw.isdigit():
            conds.append(User.id == int(raw))
        stmt = stmt.where(or_(*conds))
    rows = (await session.execute(stmt.order_by(User.last_active_at.desc().nulls_last()).offset(max(0, offset)).limit(21))).all()
    return {
        "items": [{"id": i, "name": n or "—", "username": u, "ubp": s, "banned": b, "admin": a, "last_active": _iso(la)}
                  for i, n, u, s, b, a, la in rows[:20]],
        "has_more": len(rows) > 20,
    }


@router.get("/players/{user_id}")
async def player(user_id: int, _: int = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> dict:
    from bot.db.repositories import battle_pass as pass_repo
    from bot.db.repositories import clan as clan_repo
    from bot.db.repositories.season import get_active

    u = await _target(session, user_id)
    agg = (await session.execute(text(
        "SELECT (SELECT COALESCE(SUM(quantity),0) FROM user_cards WHERE user_id=:u), "
        "(SELECT COUNT(DISTINCT card_id) FROM user_cards WHERE user_id=:u AND quantity>0), "
        "(SELECT COALESCE(SUM(amount_rub),0) FROM payments WHERE user_id=:u AND status='succeeded'), "
        "(SELECT COUNT(*) FROM users WHERE referred_by_id=:u)"
    ), {"u": user_id})).one()
    txs = (await session.execute(
        select(Transaction.currency, Transaction.amount, Transaction.reason, Transaction.created_at, Transaction.admin_id)
        .where(Transaction.user_id == user_id).order_by(Transaction.created_at.desc()).limit(25)
    )).all()
    season = await get_active(session)
    premium = False
    if season:
        row = await pass_repo.get_or_create(session, user_id=user_id, season_id=season.id)
        premium = row.is_premium
    return {
        "id": u.id, "name": u.display_name, "username": u.username, "universe": u.universe_selected,
        "clan": await clan_repo.get_name(session, u.clan_id),
        "ubp_season": u.ubp_season, "ubp_total": u.ubp_total, "dust": u.dust, "coins": u.coins, "tickets": u.tickets_count,
        "rolls": u.total_rolls, "banned": u.is_banned, "admin": u.is_admin, "config_admin": u.id in _settings.admin_ids,
        "subscription_until": _iso(u.subscription_until), "battle_pass": premium,
        "created_at": _iso(u.created_at), "last_active": _iso(u.last_active_at),
        "cards_total": int(agg[0]), "cards_unique": int(agg[1]), "donated_rub": int(agg[2]), "referrals": int(agg[3]),
        "transactions": [{"currency": getattr(c, "value", c), "amount": a, "reason": r, "at": _iso(t), "by_admin": bool(ad)} for c, a, r, t, ad in txs],
    }


class CurrencyIn(BaseModel):
    currency: str  # dust | coins | tickets
    amount: int  # может быть отрицательным — забрать (баланс не уходит ниже 0)


@router.post("/players/{user_id}/currency")
async def player_currency(user_id: int, body: CurrencyIn, admin_id: int = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> dict:
    from bot.constant.admin import TRANSACTION_REASON_ADMIN_GRANT_COINS, TRANSACTION_REASON_ADMIN_GRANT_DUST, TRANSACTION_REASON_ADMIN_GRANT_TICKETS
    from bot.db.repositories.user import apply_coins_delta, apply_dust_delta
    from bot.services import ticket

    await _target(session, user_id)
    if body.amount == 0:
        raise bad("Количество не может быть 0.")
    if body.currency == "dust":
        await apply_dust_delta(session, user_id=user_id, delta=body.amount)
        cur, reason = TransactionCurrency.dust, TRANSACTION_REASON_ADMIN_GRANT_DUST
    elif body.currency == "coins":
        await apply_coins_delta(session, user_id=user_id, delta=body.amount)
        cur, reason = TransactionCurrency.coins, TRANSACTION_REASON_ADMIN_GRANT_COINS
    elif body.currency == "tickets":
        await ticket.grant(session, user_id, body.amount)
        cur, reason = TransactionCurrency.tickets, TRANSACTION_REASON_ADMIN_GRANT_TICKETS
    else:
        raise bad("Неизвестная валюта.")
    session.add(Transaction(user_id=user_id, currency=cur, amount=body.amount, reason=reason, admin_id=admin_id))
    await session.commit()
    return {"message": f"{'Выдано' if body.amount > 0 else 'Списано'}: {abs(body.amount)}"}


@router.post("/players/{user_id}/battle-pass")
async def player_battle_pass(user_id: int, _: int = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> dict:
    from bot.db.repositories import battle_pass as pass_repo
    from bot.db.repositories.season import get_active

    await _target(session, user_id)
    season = await get_active(session)
    if season is None:
        raise bad("Нет активного сезона.")
    row = await pass_repo.get_or_create(session, user_id=user_id, season_id=season.id)
    if row.is_premium:
        raise bad("У игрока уже есть Battle Pass этого сезона.")
    await pass_repo.set_premium(session, user_id=user_id, season_id=season.id)
    await session.commit()
    return {"message": "Battle Pass выдан."}


class DaysIn(BaseModel):
    days: int


@router.post("/players/{user_id}/subscription")
async def player_subscription(user_id: int, body: DaysIn, _: int = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> dict:
    from bot.db.repositories.user import extend_subscription

    await _target(session, user_id)
    if not 0 < body.days <= 3650:
        raise bad("Дней: от 1 до 3650.")
    until = await extend_subscription(session, user_id=user_id, days=body.days)
    await session.commit()
    return {"message": f"Подписка до {until:%d.%m.%Y}"}


class FlagIn(BaseModel):
    value: bool


@router.post("/players/{user_id}/ban")
async def player_ban(user_id: int, body: FlagIn, admin_id: int = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> dict:
    from bot.db.repositories.user import set_is_banned

    await _target(session, user_id)
    if user_id in _settings.admin_ids or user_id == admin_id:
        raise bad("Нельзя забанить супер-админа или себя.")
    await set_is_banned(session, user_id=user_id, enabled=body.value)
    await session.commit()
    return {"message": "Игрок забанен." if body.value else "Бан снят."}


@router.post("/players/{user_id}/admin")
async def player_admin(user_id: int, body: FlagIn, _: int = Depends(require_super), session: AsyncSession = Depends(get_session)) -> dict:
    from bot.db.repositories.user import set_is_admin
    from bot.utils.notify import notify

    await _target(session, user_id)
    await set_is_admin(session, user_id=user_id, enabled=body.value)
    await session.commit()
    bot = _bot()
    try:
        await notify(bot, user_id, "👑 Тебе выданы права администратора." if body.value else "Права администратора отозваны.")
    finally:
        await bot.session.close()
    return {"message": "Права выданы." if body.value else "Права отозваны."}


class CardIn(BaseModel):
    card_id: int
    stars: int = 1
    qty: int = 1  # отрицательное — забрать


@router.post("/players/{user_id}/card")
async def player_card(user_id: int, body: CardIn, _: int = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> dict:
    from bot.config.game import MAX_STARS
    from bot.db.repositories.inventory import add_card, decrement_by

    await _target(session, user_id)
    if not 1 <= body.stars <= MAX_STARS or body.qty == 0 or abs(body.qty) > 10000:
        raise bad("Проверь звёзды (1–5) и количество.")
    if await session.get(Card, body.card_id) is None:
        raise bad("Карта не найдена.")
    if body.qty > 0:
        await add_card(session, user_id=user_id, card_id=body.card_id, stars=body.stars, qty=body.qty)
    elif not await decrement_by(session, user_id=user_id, card_id=body.card_id, stars=body.stars, amount=-body.qty):
        raise bad("У игрока нет столько копий.")
    await session.commit()
    return {"message": "Карта выдана." if body.qty > 0 else "Карты забраны."}


class UniverseIn(BaseModel):
    universe: str


@router.post("/players/{user_id}/universe-collection")
async def player_universe(user_id: int, body: UniverseIn, _: int = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> dict:
    from bot.db.repositories.inventory import grant_universe_collection

    await _target(session, user_id)
    count = await grant_universe_collection(session, user_id=user_id, universe_code=body.universe)
    await session.commit()
    return {"message": f"Выдано карт: {count}"}


class TextIn(BaseModel):
    text: str


@router.post("/players/{user_id}/message")
async def player_message(user_id: int, body: TextIn, _: int = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> dict:
    from bot.utils.notify import notify

    await _target(session, user_id)
    if not body.text.strip():
        raise bad("Пустое сообщение.")
    bot = _bot()
    try:
        await notify(bot, user_id, f"✉️ <b>Сообщение от администрации</b>\n\n{body.text.strip()[:3500]}")
    finally:
        await bot.session.close()
    return {"message": "Отправлено."}


@router.post("/players/{user_id}/delete")
async def player_delete(user_id: int, admin_id: int = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> dict:
    from bot.services.admin.delete_account import OwnerBlockedError, delete_account

    await _target(session, user_id)
    if user_id in _settings.admin_ids or user_id == admin_id:
        raise bad("Нельзя удалить супер-админа или себя.")
    try:
        await delete_account(session, user_id=user_id)
    except OwnerBlockedError:
        raise bad("Игрок — владелец клана с участниками. Сначала передайте владение.")
    return {"message": "Аккаунт удалён."}


# ---------------------------------------------------------------- карты (выбор для выдачи)

@router.get("/universes")
async def universes(_: int = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> list[dict]:
    from bot.db.repositories.universe import list_all

    return [{"code": u.code, "title": u.title, "active": u.is_active, "event": u.is_event} for u in await list_all(session)]


@router.get("/cards")
async def cards(universe: str, q: str = "", _: int = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> list[dict]:
    stmt = select(Card).where(Card.universe_code == universe)
    if q.strip():
        stmt = stmt.where(or_(Card.name.ilike(f"%{q.strip()}%"), Card.external_id == q.strip()))
    rows = (await session.execute(stmt.order_by(Card.base_ubp.desc(), Card.external_id).limit(60))).scalars().all()
    return [{"id": c.id, "external_id": c.external_id, "name": c.name, "base_ubp": c.base_ubp,
             "image_url": f"/api/img/{c.image_path}?w=160", "special": c.is_celestial or c.is_divine} for c in rows]


# ---------------------------------------------------------------- массовые действия

class MassIn(BaseModel):
    currency: str
    amount: int


@router.post("/mass-grant")
async def mass_grant(body: MassIn, admin_id: int = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> dict:
    from bot.services.admin import mass_grant as mg

    if body.amount <= 0:
        raise bad("Количество должно быть больше 0.")
    fn = {"dust": mg.mass_grant_dust, "coins": mg.mass_grant_coins, "tickets": mg.mass_grant_tickets}.get(body.currency)
    if fn is None:
        raise bad("Неизвестная валюта.")
    count = await fn(session, amount=body.amount, admin_id=admin_id)
    return {"message": f"Выдано {count} игрокам."}


async def _broadcast_bg(text_: str, admin_id: int) -> None:
    from bot.services.broadcast import run_broadcast
    from bot.utils.notify import notify

    bot = _bot()
    try:
        async with session_factory() as session:
            sent, failed = await run_broadcast(bot, session, text_)
        await notify(bot, admin_id, f"📣 Рассылка завершена: доставлено {sent}, ошибок {failed}.")
    except Exception:
        log.exception("mini app broadcast failed")
    finally:
        await bot.session.close()


@router.post("/broadcast")
async def broadcast(body: TextIn, admin_id: int = Depends(require_admin)) -> dict:
    if not body.text.strip():
        raise bad("Пустой текст.")
    _spawn(_broadcast_bg(body.text.strip(), admin_id))
    return {"message": "Рассылка запущена — итог придёт в бота."}


# ---------------------------------------------------------------- промокоды

@router.get("/promos")
async def promos(_: int = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> list[dict]:
    from bot.services.promo import list_status

    return [{"code": p.code, "active": p.is_active, "deactivated": p.deactivated, "dust": p.dust, "coins": p.coins,
             "tickets": p.tickets, "max_uses": p.max_uses, "used": p.used_count} for p in await list_status(session, limit=50)]


class PromoIn(BaseModel):
    code: str
    type: str  # uses | time | users
    param: str  # число активаций / часов / username через запятую
    reward: dict[str, int]


@router.post("/promos")
async def promo_create(body: PromoIn, _: int = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> dict:
    from bot.services.promo import PromoTakenError, create_promo

    code = body.code.strip()
    reward = {k: v for k, v in body.reward.items() if k in ("dust", "coins", "tickets") and v}
    if not code or " " in code or len(code) > 32:
        raise bad("Код: без пробелов, до 32 символов.")
    if not reward:
        raise bad("Укажи хотя бы одну награду.")
    max_uses = expires = users = None
    if body.type == "uses":
        if not body.param.isdigit() or int(body.param) <= 0:
            raise bad("Число активаций — целое > 0.")
        type_, max_uses = PromoCodeType.uses, int(body.param)
    elif body.type == "time":
        if not body.param.isdigit() or int(body.param) <= 0:
            raise bad("Часы — целое > 0.")
        type_, expires = PromoCodeType.time, datetime.now(timezone.utc) + timedelta(hours=int(body.param))
    elif body.type == "users":
        users = [x.strip().lstrip("@").lower() for x in body.param.split(",") if x.strip()]
        if not users:
            raise bad("Список username пуст.")
        type_ = PromoCodeType.user_list
    else:
        raise bad("Неизвестный тип.")
    try:
        await create_promo(session, code=code, type_=type_, max_uses=max_uses, expires_at=expires, allowed_usernames=users, reward=reward)
    except PromoTakenError:
        raise bad("Такой код уже есть.")
    return {"message": f"Промокод {code} создан."}


@router.post("/promos/{code}/{action}")
async def promo_action(code: str, action: str, _: int = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> dict:
    from bot.services import promo

    fn = {"activate": promo.activate_promo, "deactivate": promo.deactivate_promo, "delete": promo.delete_promo}.get(action)
    if fn is None:
        raise bad("Неизвестное действие.")
    await fn(session, code=code)
    return {"message": {"activate": "Включён.", "deactivate": "Выключен.", "delete": "Удалён."}[action]}


# ---------------------------------------------------------------- рефералы

@router.get("/referrals")
async def referrals(_: int = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> list[dict]:
    from bot.services.referral import get_campaign_stats, list_links_with_stats

    out = []
    for code, *_rest in await list_links_with_stats(session):
        s = await get_campaign_stats(session, code)
        if s:
            out.append({"code": s.code, "visited": s.visited, "playing": s.playing, "subs": s.subscriptions_bought,
                        "passes": s.battle_passes_bought, "donated": s.donated_coins})
    bot = _bot()
    try:
        username = (await bot.get_me()).username
    finally:
        await bot.session.close()
    for row in out:
        row["link"] = f"https://t.me/{username}?start=ref_{row['code']}"
    return out


class CodeIn(BaseModel):
    code: str


@router.post("/referrals")
async def referral_create(body: CodeIn, admin_id: int = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> dict:
    from bot.services.referral import create_link

    code = body.code.strip()
    if not code.replace("_", "").isalnum() or len(code) > 32:
        raise bad("Код: латиница/цифры/_, до 32 символов.")
    try:
        await create_link(session, code=code, admin_id=admin_id)
    except Exception:
        await session.rollback()
        raise bad("Не удалось создать (код занят?).")
    return {"message": f"Кампания {code} создана."}


# ---------------------------------------------------------------- сезон и ивенты

class VersionIn(BaseModel):
    version: str


@router.post("/season/new")
async def season_new(body: VersionIn, _: int = Depends(require_super), session: AsyncSession = Depends(get_session)) -> dict:
    from bot.handlers.admin.season import _notify_season_change
    from bot.services import season as season_service

    version = body.version.strip()
    if not 0 < len(version) <= 16:
        raise bad("Версия: 1–16 символов.")
    _new, rewards = await season_service.start_new_season(session, version=version)

    async def notify_bg() -> None:
        bot = _bot()
        try:
            await _notify_season_change(bot, session_factory, version=version, rewards=rewards)
        except Exception:
            log.exception("season notify failed")
        finally:
            await bot.session.close()

    _spawn(notify_bg())
    return {"message": f"Сезон {version} начат. Наград топа: {len(rewards)}."}


@router.post("/season/bump")
async def season_bump(body: VersionIn, _: int = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> dict:
    from bot.services import season as season_service

    version = body.version.strip()
    if not 0 < len(version) <= 16:
        raise bad("Версия: 1–16 символов.")
    try:
        await season_service.bump_version(session, version=version)
    except season_service.NoActiveSeasonError:
        raise bad("Нет активного сезона.")
    return {"message": f"Версия сезона: {version}"}


@router.get("/events")
async def events(_: int = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> list[dict]:
    from bot.services.event import list_status

    return [{"code": e.code, "title": e.title, "active": e.is_active} for e in await list_status(session)]


@router.post("/events/{code}")
async def event_toggle(code: str, body: ToggleIn, _: int = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> dict:
    from bot.services.event import list_status, set_active
    from bot.texts.admin import EVENT_START_BROADCAST

    current = next((e for e in await list_status(session) if e.code == code), None)
    if current is None:
        raise bad("Ивент не найден.")
    await set_active(session, code=code, active=body.enabled)
    if body.enabled:
        async def announce() -> None:
            from bot.services.broadcast import run_broadcast

            bot = _bot()
            try:
                async with session_factory() as s:
                    await run_broadcast(bot, s, EVENT_START_BROADCAST.format(title=current.title))
            except Exception:
                log.exception("event announce failed")
            finally:
                await bot.session.close()

        _spawn(announce())
    return {"message": f"{current.title}: {'включён' if body.enabled else 'выключен'}"}


# ---------------------------------------------------------------- платежи и админы

@router.get("/payments")
async def payments(offset: int = 0, _: int = Depends(require_admin), session: AsyncSession = Depends(get_session)) -> dict:
    rows = (await session.execute(text(
        "SELECT p.id, p.user_id, COALESCE(u.display_name, u.username, p.user_id::text), p.amount_rub, p.coins_amount, "
        "p.item_kind::text, p.status::text, p.created_at FROM payments p LEFT JOIN users u ON u.id = p.user_id "
        "ORDER BY p.created_at DESC OFFSET :o LIMIT 31"
    ), {"o": max(0, offset)})).all()
    return {
        "items": [{"id": i, "user_id": u, "name": n, "rub": r, "coins": c, "kind": k, "status": s, "at": _iso(t)}
                  for i, u, n, r, c, k, s, t in rows[:30]],
        "has_more": len(rows) > 30,
    }


@router.get("/admins")
async def admins(_: int = Depends(require_super), session: AsyncSession = Depends(get_session)) -> list[dict]:
    from bot.db.repositories.user import get_many_by_ids, list_admins

    db_admins = await list_admins(session)
    cfg = await get_many_by_ids(session, list(_settings.admin_ids))
    out = [{"id": i, "name": (cfg[i].display_name if i in cfg else None) or str(i), "super": True} for i in sorted(_settings.admin_ids)]
    out += [{"id": u.id, "name": u.display_name or str(u.id), "super": False} for u in db_admins if u.id not in _settings.admin_ids]
    return out
