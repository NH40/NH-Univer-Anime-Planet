"""Игровые действия Mini App (новый дизайн, 2026-10-20): крутки (×1/×5/×10/все), выбор вселенной,
слияния, распыление, задания, ежедневный бонус, топ, магазин, небесные карты, клан (просмотр).

Это второе (после `battle_pass`) осознанное расширение Mini App с read-only до действий —
пользователь просил «весь функционал в приложении». Своей игровой логики здесь НЕТ: каждый
эндпоинт вызывает тот же сервис, что хендлер бота, с теми же Redis-локами от двойных тапов.
"""
from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user_id
from api.db import get_session
from api.deps import get_redis
from bot.cache.keys import action_lock
from bot.cache.lock import try_acquire
from bot.config.game import MASS_ROLL_COUNTS, MASS_ROLL_MAX, SHOP_COIN_TICKET_PRICE, SHOP_TICKET_PRICE_DUST, TIER_CHANCE_PERCENT
from bot.constant.deck import LOCK_ACTION_ROLL
from bot.db.models.card import Card
from bot.db.models.user import User
from bot.db.repositories.season import get_active as get_active_season
from bot.db.repositories.universe import list_active as list_active_universes
from bot.db.repositories.user import get_by_id, set_universe
from bot.services import ticket
from bot.services.card import UniverseNotReadyError
from bot.services.gacha import NoActiveSeasonError, NotEnoughTicketsError, roll_many

router = APIRouter(prefix="/api", tags=["game"])

TIER_NAMES = {6000: "Мифический", 5000: "Легендарный", 4000: "Эпический", 3000: "Редкий", 2000: "Необычный", 1000: "Обычный"}


def bad(msg: str) -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, msg)


async def _user(session: AsyncSession, user_id: int) -> User:
    user = await get_by_id(session, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Сначала нажми /start в боте.")
    return user


def card_out(card: Card, **extra) -> dict:
    return {
        "card_id": card.id, "external_id": card.external_id, "name": card.name, "base_ubp": card.base_ubp,
        "universe": card.universe_code, "is_celestial": card.is_celestial, "is_divine": card.is_divine,
        "image_url": f"/api/img/{card.image_path}?w=320", "image_full": f"/api/img/{card.image_path}?w=720", **extra,
    }


# ---------------------------------------------------------------- крутки

class RollIn(BaseModel):
    count: str = "1"  # "1" | "5" | "10" | "all"


class UniverseIn(BaseModel):
    code: str


@router.get("/roll")
async def get_roll(user_id: int = Depends(get_current_user_id), session: AsyncSession = Depends(get_session)) -> dict:
    user = await _user(session, user_id)
    st = await ticket.get_status(session, user_id)
    await session.commit()  # get_status лениво начисляет реген
    return {
        "universe": user.universe_selected,
        "universes": [{"code": u.code, "title": u.title} for u in await list_active_universes(session)],
        "tickets": st.count, "cap": st.cap, "next_in": st.seconds_until_next,
        "chances": [{"tier": t, "name": TIER_NAMES.get(t, str(t)), "percent": p} for t, p in sorted(TIER_CHANCE_PERCENT.items(), reverse=True)],
        "mass_counts": list(MASS_ROLL_COUNTS), "mass_max": MASS_ROLL_MAX,
    }


@router.post("/universe")
async def post_universe(body: UniverseIn, user_id: int = Depends(get_current_user_id), session: AsyncSession = Depends(get_session)) -> dict:
    await _user(session, user_id)
    if body.code not in {u.code for u in await list_active_universes(session)}:
        raise bad("Неизвестная вселенная.")
    await set_universe(session, user_id=user_id, universe_code=body.code)
    await session.commit()
    return {"message": "Вселенная выбрана."}


@router.post("/roll")
async def post_roll(
    body: RollIn, user_id: int = Depends(get_current_user_id), session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> dict:
    user = await _user(session, user_id)
    if not user.universe_selected:
        raise bad("Сначала выбери вселенную.")
    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_ROLL), ttl_ms=90_000) as acquired:
        if not acquired:
            raise bad("Крутка уже идёт…")
        if body.count == "all":
            count = min(await ticket.get_balance(session, user_id), MASS_ROLL_MAX)
            await session.commit()
        elif body.count == "1" or (body.count.isdigit() and int(body.count) in MASS_ROLL_COUNTS):
            count = int(body.count)
        else:
            raise bad("Неизвестное количество.")
        try:
            results = await roll_many(session, redis, user_id=user_id, universe_code=user.universe_selected, count=max(1, count))
        except NoActiveSeasonError:
            raise bad("Сезон ещё не начался.")
        except UniverseNotReadyError:
            raise bad("Вселенная ещё не готова для круток.")
        except NotEnoughTicketsError:
            raise bad("Не хватает тикетов.")
    balance = await ticket.get_balance(session, user_id)
    await session.commit()
    cards = [
        card_out(r.card, stars=r.stars, is_new=r.owned_quantity == 1, celestial=("owner" if r.celestial_outcome.became_owner else "challenger") if r.celestial_outcome else None,
                 divine=[card_out(d) for d in (r.universe_divine_card, r.global_divine_card) if d is not None])
        for r in results
    ]
    tiers = Counter(r.card.base_ubp for r in results if not r.card.is_celestial and not r.card.is_divine)
    return {
        "cards": cards, "tickets": balance, "requested": count, "ubp": sum(r.card.base_ubp for r in results),
        "new": sum(1 for c in cards if c["is_new"]),
        "tiers": [{"tier": t, "name": TIER_NAMES.get(t, str(t)), "count": n} for t, n in sorted(tiers.items(), reverse=True)],
    }


# ---------------------------------------------------------------- слияния и распыление

class MergeIn(BaseModel):
    card_id: int
    stars: int
    target_stars: int
    single: bool = True


class MergeAllIn(BaseModel):
    universe: str


class DustIn(BaseModel):
    card_id: int | None = None
    stars: int | None = None
    amount: int | None = None  # точное число
    mode: str = "amount"  # amount | duplicates | all | owned_duplicates | owned_all


@router.post("/merge")
async def post_merge(
    body: MergeIn, user_id: int = Depends(get_current_user_id), session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> dict:
    from bot.services import merge as merge_svc

    try:
        r = await merge_svc.merge_to_target(
            session, redis, user_id=user_id, card_id=body.card_id, stars=body.stars, target_stars=body.target_stars, single=body.single
        )
    except merge_svc.NotEnoughCopiesError:
        raise bad("Не хватает копий для слияния.")
    except (merge_svc.CardNotFoundError, merge_svc.InvalidTargetError):
        raise bad("Так слить нельзя.")
    except merge_svc.NoActiveSeasonError:
        raise bad("Сезон ещё не начался.")
    return {"message": f"{r.card.name}: слито {r.events} раз, теперь ★{r.final_stars}. +{r.total_bonus} UBP"}


@router.post("/merge/all")
async def post_merge_all(
    body: MergeAllIn, user_id: int = Depends(get_current_user_id), session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> dict:
    from bot.services import merge as merge_svc

    try:
        rs = await merge_svc.merge_all_to_max_in_universe(session, redis, user_id=user_id, universe_code=body.universe)
    except merge_svc.NoActiveSeasonError:
        raise bad("Сезон ещё не начался.")
    if not rs:
        raise bad("Сливать нечего — нигде нет 5 одинаковых копий.")
    return {"message": f"Слияний: {sum(r.events for r in rs)} · +{sum(r.total_bonus for r in rs)} UBP"}


@router.post("/dust")
async def post_dust(body: DustIn, user_id: int = Depends(get_current_user_id), session: AsyncSession = Depends(get_session)) -> dict:
    from bot.services import dust as dust_svc

    try:
        if body.mode == "amount":
            if body.card_id is None or body.stars is None or not body.amount or body.amount <= 0:
                raise bad("Укажи карту и количество.")
            got = await dust_svc.distill_amount(session, user_id=user_id, card_id=body.card_id, stars=body.stars, amount=body.amount)
        elif body.mode in ("duplicates", "all"):
            if body.card_id is None or body.stars is None:
                raise bad("Укажи карту.")
            got = await dust_svc.distill(session, user_id=user_id, card_id=body.card_id, stars=body.stars, keep_one=body.mode == "duplicates")
        elif body.mode in ("owned_duplicates", "owned_all"):
            got = await dust_svc.distill_all_owned(session, user_id=user_id, keep_one=body.mode == "owned_duplicates")
        else:
            raise bad("Неизвестный режим.")
    except dust_svc.RelicCardError:
        raise bad("Небесные и божественные карты не распыляются.")
    except (dust_svc.NothingToDistillError, dust_svc.NotEnoughCopiesError, dust_svc.CardNotFoundError):
        raise bad("Нечего распылять.")
    return {"message": f"Распылено: +{got} пыли"}


# ---------------------------------------------------------------- задания и бонус

class SlotIn(BaseModel):
    slot: int | None = None


@router.get("/quests")
async def get_quests(user_id: int = Depends(get_current_user_id), session: AsyncSession = Depends(get_session)) -> dict:
    from bot.config.game import DAILY_BONUS_REWARDS
    from bot.services import daily_bonus, quest

    await _user(session, user_id)
    q = await quest.get_status(session, user_id)
    b = await daily_bonus.get_status(session, user_id)
    await session.commit()  # get_status может лениво переиграть набор
    return {
        "slots": [
            {"slot": s.slot, "text": s.text, "progress": min(s.progress, s.target), "target": s.target,
             "dust": s.reward_dust, "tickets": s.reward_tickets, "claimed": s.claimed, "done": s.progress >= s.target}
            for s in q.slots
        ],
        "reroll_all": q.reroll_all_available, "rerolls_left": q.individual_rerolls_left,
        "bonus": {
            "streak": 0 if (b is None or b.resets_on_claim) else b.streak, "claimable": bool(b and b.claimable),
            "next_in": b.seconds_until_claimable if b else None,
            "rewards": [{"day": i + 1, "dust": r[0], "tickets": r[1]} for i, r in enumerate(DAILY_BONUS_REWARDS)],
        },
    }


@router.post("/quests/{action}")
async def post_quest(
    action: str, body: SlotIn = SlotIn(), user_id: int = Depends(get_current_user_id), session: AsyncSession = Depends(get_session),
) -> dict:
    from bot.services import daily_bonus, quest

    try:
        if action == "claim" and body.slot is not None:
            r = await quest.claim(session, user_id=user_id, slot=body.slot)
            return {"message": f"Награда: +{r.reward_dust} пыли, +{r.reward_tickets} тикетов"}
        if action == "claim-all":
            r = await quest.claim_all(session, user_id=user_id)
            return {"message": f"Забрано заданий: {r.count} · +{r.reward_dust} пыли, +{r.reward_tickets} тикетов"}
        if action == "reroll" and body.slot is not None:
            await quest.reroll_one(session, user_id=user_id, slot=body.slot)
            return {"message": "Задание заменено."}
        if action == "reroll-all":
            await quest.reroll_all(session, user_id=user_id)
            return {"message": "Набор заданий обновлён."}
        if action == "bonus":
            r = await daily_bonus.claim(session, user_id=user_id)
            return {"message": f"День {r.day}: +{r.dust} пыли, +{r.tickets} тикетов"}
    except (quest.QuestNotDoneError, quest.NothingToClaimError):
        raise bad("Задание ещё не выполнено.")
    except quest.QuestAlreadyClaimedError:
        raise bad("Уже забрано.")
    except quest.RerollNotAvailableError:
        raise bad("Замены на сегодня закончились.")
    except daily_bonus.AlreadyClaimedError:
        raise bad("Бонус уже забран — приходи позже.")
    raise bad("Неизвестное действие.")


# ---------------------------------------------------------------- топ, магазин

@router.get("/top")
async def get_top(
    universe: str | None = None, user_id: int = Depends(get_current_user_id), session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> dict:
    from bot.cache.universe_leaderboard import get_rank, get_top as lb_top

    user = await _user(session, user_id)
    universes = await list_active_universes(session)
    code = universe or user.universe_selected or (universes[0].code if universes else None)
    season = await get_active_season(session)
    if season is None or code is None:
        return {"universe": code, "universes": [{"code": u.code, "title": u.title} for u in universes], "rows": [], "me": None}
    top = await lb_top(redis, session, season.id, code, 20)
    names = dict((await session.execute(select(User.id, User.display_name).where(User.id.in_([u for u, _ in top])))).all()) if top else {}
    return {
        "universe": code, "universes": [{"code": u.code, "title": u.title} for u in universes],
        "rows": [{"place": i + 1, "user_id": u, "name": names.get(u) or f"id{u}", "ubp": s, "is_me": u == user_id} for i, (u, s) in enumerate(top)],
        "me": await get_rank(redis, season.id, code, user_id),
    }


class BuyIn(BaseModel):
    currency: str  # dust | coins
    quantity: int


@router.get("/shop")
async def get_shop(user_id: int = Depends(get_current_user_id), session: AsyncSession = Depends(get_session)) -> dict:
    user = await _user(session, user_id)
    return {"dust": user.dust, "coins": user.coins, "dust_price": SHOP_TICKET_PRICE_DUST, "coin_price": SHOP_COIN_TICKET_PRICE, "presets": [1, 5, 10, 50]}


@router.post("/shop/tickets")
async def post_buy(body: BuyIn, user_id: int = Depends(get_current_user_id), session: AsyncSession = Depends(get_session)) -> dict:
    from bot.services import shop

    if body.quantity <= 0 or body.quantity > 1000:
        raise bad("Количество от 1 до 1000.")
    try:
        if body.currency == "dust":
            await shop.buy_tickets(session, user_id=user_id, quantity=body.quantity)
        elif body.currency == "coins":
            await shop.buy_tickets_with_coins(session, user_id=user_id, quantity=body.quantity)
        else:
            raise bad("Неизвестная валюта.")
    except shop.NotEnoughDustError:
        raise bad("Не хватает пыли.")
    except shop.NotEnoughCoinsError:
        raise bad("Не хватает коинов.")
    return {"message": f"Куплено тикетов: {body.quantity}"}


# ---------------------------------------------------------------- небесные карты, клан

@router.get("/celestial")
async def get_celestial(user_id: int = Depends(get_current_user_id), session: AsyncSession = Depends(get_session)) -> dict:
    from bot.db.repositories.celestial import list_all_statuses

    statuses = await list_all_statuses(session)
    ids = {x for s in statuses if s.ownership for x in (s.ownership.owner_id, s.ownership.challenger_id) if x}
    names = dict((await session.execute(select(User.id, User.display_name).where(User.id.in_(ids))))) if ids else {}
    titles = {u.code: u.title for u in await list_active_universes(session)}
    out: dict[str, list] = {}
    for s in statuses:
        o, b = s.ownership, s.battle
        out.setdefault(s.card.universe_code, []).append(card_out(
            s.card,
            owner=(names.get(o.owner_id) or f"id{o.owner_id}") if o else None, mine=bool(o and o.owner_id == user_id),
            challenger=(names.get(o.challenger_id) or f"id{o.challenger_id}") if o and o.challenger_id else None,
            battle=f"{b.owner_wins}:{b.challenger_wins} · игра {b.game_index + 1} из 3" if b else None,
        ))
    return {"universes": [{"code": c, "title": titles.get(c, c), "cards": cards} for c, cards in out.items()]}


@router.get("/clan")
async def get_clan(user_id: int = Depends(get_current_user_id), session: AsyncSession = Depends(get_session)) -> dict:
    from bot.services.clan import get_clan_view

    user = await _user(session, user_id)
    if not user.clan_id:
        return {"clan": None}
    view = await get_clan_view(session, user.clan_id)
    if view is None:
        return {"clan": None}
    members = (await session.execute(text(
        "SELECT u.id, COALESCE(u.display_name, u.username, u.id::text), u.ubp_season, m.rank FROM clan_members m "
        "JOIN users u ON u.id = m.user_id WHERE m.clan_id = :c ORDER BY u.ubp_season DESC"
    ), {"c": user.clan_id})).all()
    return {"clan": {
        "name": view.clan.name, "ubp_season": int(view.ubp_season), "ubp_total": int(view.ubp_total), "members": view.member_count,
        "top10": view.is_top10_all_time,
        "list": [{"id": i, "name": n, "ubp": u, "rank": str(getattr(r, "value", r)), "is_me": i == user_id} for i, n, u, r in members],
    }}
