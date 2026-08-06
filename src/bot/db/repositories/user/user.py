from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import case, func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.transaction import Transaction
from bot.db.models.user import User


async def get_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def get_many_by_ids(session: AsyncSession, user_ids: list[int]) -> dict[int, User]:
    if not user_ids:
        return {}
    result = await session.execute(select(User).where(User.id.in_(user_ids)))
    return {u.id: u for u in result.scalars().all()}


async def get_by_username(session: AsyncSession, username: str) -> User | None:
    """Регистронезависимый поиск (username в Telegram регистронезависим). Не уникальный
    констрейнт в БД (username может смениться) — при коллизии берём первого попавшегося,
    это редкий и не критичный edge case для приглашений/обменника."""
    result = await session.execute(select(User).where(User.username.ilike(username)).limit(1))
    return result.scalar_one_or_none()


async def upsert_from_telegram(
    session: AsyncSession, *, user_id: int, username: str | None, display_name: str
) -> User:
    """Регистрация/обновление игрока при каждом /start. Атомарный upsert одним запросом —
    без гонки "проверили что нет — вставили" при параллельных апдейтах от одного пользователя."""
    stmt = (
        pg_insert(User)
        .values(id=user_id, username=username, display_name=display_name)
        .on_conflict_do_update(
            index_elements=[User.id],
            set_={"username": username},
        )
        .returning(User)
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.scalar_one()


async def set_universe(session: AsyncSession, *, user_id: int, universe_code: str) -> None:
    await session.execute(update(User).where(User.id == user_id).values(universe_selected=universe_code))
    await session.commit()


async def set_display_name(session: AsyncSession, *, user_id: int, display_name: str) -> None:
    await session.execute(update(User).where(User.id == user_id).values(display_name=display_name))
    await session.commit()


async def set_clan(session: AsyncSession, *, user_id: int, clan_id: int | None) -> None:
    """Не коммитит — часть композитной операции (создание/вступление/выход из клана,
    см. services/clan)."""
    await session.execute(update(User).where(User.id == user_id).values(clan_id=clan_id))


async def spend_dust(session: AsyncSession, *, user_id: int, amount: int) -> bool:
    """Атомарно списывает пыль, только если хватает. True — списали, False — не хватило.
    Не коммитит — композируется в сервисах магазина (см. CLAUDE.md, правило 10)."""
    result = await session.execute(
        update(User)
        .where(User.id == user_id, User.dust >= amount)
        .values(dust=User.dust - amount)
        .returning(User.id)
    )
    return result.scalar_one_or_none() is not None


async def add_dust(session: AsyncSession, *, user_id: int, amount: int) -> None:
    """Начисляет пыль (обменник в клане, награда за войну и т.п.). Не коммитит."""
    await session.execute(update(User).where(User.id == user_id).values(dust=User.dust + amount))


async def spend_coins(session: AsyncSession, *, user_id: int, amount: int) -> bool:
    """Атомарно списывает коины, только если хватает. Не коммитит — см. spend_dust."""
    result = await session.execute(
        update(User)
        .where(User.id == user_id, User.coins >= amount)
        .values(coins=User.coins - amount)
        .returning(User.id)
    )
    return result.scalar_one_or_none() is not None


async def add_coins(session: AsyncSession, *, user_id: int, amount: int) -> None:
    """Начисляет коины (награда сезонного пасса и т.п.). Не коммитит — см. add_dust."""
    await session.execute(update(User).where(User.id == user_id).values(coins=User.coins + amount))


_EXTEND_SUBSCRIPTION_SQL = text(
    """
    UPDATE users
    SET subscription_until = GREATEST(COALESCE(subscription_until, now()), now()) + (:days * INTERVAL '1 day'),
        subscription_ticket_granted_at = COALESCE(subscription_ticket_granted_at, now())
    WHERE id = :user_id
    RETURNING subscription_until
    """
)


async def extend_subscription(session: AsyncSession, *, user_id: int, days: int) -> datetime:
    """Продлевает подписку на `days` от МАКСИМУМА(текущее истечение, сейчас) — то есть
    покупки стакаются: если подписка ещё активна, дни добавляются поверх остатка, а не
    просто сдвигают дату от "сейчас" (иначе повторная покупка перед самым концом почти
    ничего бы не добавляла). Заодно выставляет `subscription_ticket_granted_at` — но ТОЛЬКО
    если он ещё NULL (первая подписка вообще), чтобы продление уже активной подписки не
    сбрасывало таймер суточного начисления тикетов (см. CLAUDE.md, "Подписка"). Не коммитит."""
    result = await session.execute(_EXTEND_SUBSCRIPTION_SQL, {"user_id": user_id, "days": days})
    return result.scalar_one()


async def increment_total_rolls(session: AsyncSession, *, user_id: int, amount: int) -> tuple[int, int | None]:
    """Накопительный счётчик "круток за всё время" для профиля. Не коммитит — вызывается
    внутри services/gacha как часть одной композитной операции крутки.

    Возвращает (новый total_rolls, referred_by_id) тем же UPDATE — services/gacha по
    `new_total_rolls == amount` бесплатно узнаёт "это была самая первая крутка вообще"
    (старое значение было 0), без отдельного SELECT перед инкрементом — нужно для
    реферальной награды "50 коинов+50 тикетов за первую крутку приглашённого"."""
    result = await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(total_rolls=User.total_rolls + amount)
        .returning(User.total_rolls, User.referred_by_id)
    )
    return result.one()


async def set_notify_tickets_full(session: AsyncSession, *, user_id: int, enabled: bool) -> None:
    """Тумблер "Настройки -> Уведомления" (см. handlers/settings). Коммитит — самостоятельное
    единичное действие, не часть составной операции."""
    await session.execute(update(User).where(User.id == user_id).values(notify_tickets_full=enabled))
    await session.commit()


async def set_notify_roll_reminder(session: AsyncSession, *, user_id: int, enabled: bool) -> None:
    await session.execute(update(User).where(User.id == user_id).values(notify_roll_reminder=enabled))
    await session.commit()


async def set_notify_clan_requests(session: AsyncSession, *, user_id: int, enabled: bool) -> None:
    await session.execute(update(User).where(User.id == user_id).values(notify_clan_requests=enabled))
    await session.commit()


async def set_notify_daily_bonus(session: AsyncSession, *, user_id: int, enabled: bool) -> None:
    await session.execute(update(User).where(User.id == user_id).values(notify_daily_bonus=enabled))
    await session.commit()


async def set_is_admin(session: AsyncSession, *, user_id: int, enabled: bool) -> bool:
    """True — обновили (юзер существует), False — юзера с таким id нет (см. handlers/admin,
    выдача админки по username сначала резолвит username в id через get_by_username)."""
    result = await session.execute(
        update(User).where(User.id == user_id).values(is_admin=enabled).returning(User.id)
    )
    ok = result.scalar_one_or_none() is not None
    await session.commit()
    return ok


async def set_is_banned(session: AsyncSession, *, user_id: int, enabled: bool) -> bool:
    result = await session.execute(
        update(User).where(User.id == user_id).values(is_banned=enabled).returning(User.id)
    )
    ok = result.scalar_one_or_none() is not None
    await session.commit()
    return ok


async def count_all(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(User.id)))
    return result.scalar_one()


async def count_active_since(session: AsyncSession, since: datetime) -> int:
    """"Онлайн" в статистике /admin — активны за окно `since..now` (см. CLAUDE.md,
    "Админ-панель"), не буквальное текущее подключение (у long-polling бота такого
    понятия нет)."""
    result = await session.execute(select(func.count(User.id)).where(User.last_active_at >= since))
    return result.scalar_one()


async def list_all_ids(session: AsyncSession) -> list[int]:
    """Для рассылки (см. services/broadcast) — только id, не полные строки: на 30k
    игроков список int'ов копеечный по памяти, а тянуть весь User целиком незачем."""
    result = await session.execute(select(User.id))
    return list(result.scalars().all())


async def set_referred_by(session: AsyncSession, *, user_id: int, referrer_id: int) -> None:
    """Выставляет referred_by_id ровно один раз (WHERE referred_by_id IS NULL) — повторный
    /start по чужой реферальной ссылке уже привязанного игрока ничего не меняет. Нельзя
    указать себя же реферером (referrer_id == user_id молча игнорируется на уровне вызова,
    см. handlers/start). Коммитит — самостоятельная операция."""
    await session.execute(
        update(User)
        .where(User.id == user_id, User.referred_by_id.is_(None))
        .values(referred_by_id=referrer_id)
    )
    await session.commit()


@dataclass
class ReferralStats:
    invited: int
    playing: int  # total_rolls > 0
    donors: int  # хотя бы один успешный платёж (payments.status = succeeded)
    subscribers: int  # subscription_until > now() ПРЯМО СЕЙЧАС (живой снимок, не "когда-либо")
    battle_pass_owners: int  # BattlePass.is_premium в АКТИВНОМ сезоне
    coins_earned: int
    tickets_earned: int


async def get_referral_stats(
    session: AsyncSession, user_id: int, *, reward_reasons: tuple[str, ...], active_season_id: int | None
) -> ReferralStats:
    """Подробная статистика по рефералам игрока (см. запрос пользователя 2026-08-06: не
    только "перешло/играет", а ещё доноры/подписчики/владельцы пасса/заработок). Несколько
    небольших запросов вместо одного гигантского с кучей LEFT JOIN — это не горячий путь
    (открывается по кнопке одним игроком за раз), читаемость важнее экономии одного round-trip."""
    from bot.db.models.battle_pass import BattlePass
    from bot.db.models.enums import PaymentStatus
    from bot.db.models.payment import Payment

    base_stmt = select(
        func.count(User.id),
        func.count(User.id).filter(User.total_rolls > 0),
        func.count(User.id).filter(User.subscription_until > func.now()),
    ).where(User.referred_by_id == user_id)
    invited, playing, subscribers = (await session.execute(base_stmt)).one()

    donors_stmt = (
        select(func.count(func.distinct(Payment.user_id)))
        .select_from(Payment)
        .join(User, User.id == Payment.user_id)
        .where(User.referred_by_id == user_id, Payment.status == PaymentStatus.succeeded)
    )
    donors = (await session.execute(donors_stmt)).scalar_one()

    battle_pass_owners = 0
    if active_season_id is not None:
        bp_stmt = (
            select(func.count(BattlePass.user_id))
            .select_from(BattlePass)
            .join(User, User.id == BattlePass.user_id)
            .where(
                User.referred_by_id == user_id,
                BattlePass.season_id == active_season_id,
                BattlePass.is_premium.is_(True),
            )
        )
        battle_pass_owners = (await session.execute(bp_stmt)).scalar_one()

    earned_stmt = select(
        func.coalesce(
            func.sum(case((Transaction.currency == "coins", Transaction.amount), else_=0)), 0
        ),
        func.coalesce(
            func.sum(case((Transaction.currency == "tickets", Transaction.amount), else_=0)), 0
        ),
    ).where(Transaction.user_id == user_id, Transaction.reason.in_(reward_reasons))
    coins_earned, tickets_earned = (await session.execute(earned_stmt)).one()

    return ReferralStats(
        invited=int(invited),
        playing=int(playing),
        donors=int(donors),
        subscribers=int(subscribers),
        battle_pass_owners=int(battle_pass_owners),
        coins_earned=int(coins_earned),
        tickets_earned=int(tickets_earned),
    )
