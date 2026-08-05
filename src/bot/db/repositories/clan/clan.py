from __future__ import annotations

from datetime import datetime

from sqlalchemy import func as sa_func
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.clan import Clan, ClanJoinRequest, ClanMember, ClanWar
from bot.db.models.enums import ClanRank, ClanWarStatus
from bot.db.models.user import User

_UNSET = object()  # сентинел "параметр не передан", отличимый от осознанного None

# --- Clan ---


async def get_by_id(session: AsyncSession, clan_id: int) -> Clan | None:
    return await session.get(Clan, clan_id)


async def get_many_by_ids(session: AsyncSession, clan_ids: list[int]) -> dict[int, Clan]:
    if not clan_ids:
        return {}
    result = await session.execute(select(Clan).where(Clan.id.in_(clan_ids)))
    return {c.id: c for c in result.scalars().all()}


async def get_name(session: AsyncSession, clan_id: int | None) -> str | None:
    """Удобная обёртка для мест, которым нужно только имя (например, профиль игрока)."""
    if clan_id is None:
        return None
    clan = await session.get(Clan, clan_id)
    return clan.name if clan else None


async def create(session: AsyncSession, *, name: str, owner_id: int) -> Clan | None:
    """Атомарный insert — None, если имя уже занято (ON CONFLICT DO NOTHING), а не
    "проверили что нет — вставили" (гонка при одновременном создании двух одноимённых
    кланов). Не коммитит — часть композитной операции создания клана (см. services/clan)."""
    stmt = (
        pg_insert(Clan)
        .values(name=name, owner_id=owner_id)
        .on_conflict_do_nothing(index_elements=[Clan.name])
        .returning(Clan)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def set_owner(session: AsyncSession, *, clan_id: int, owner_id: int) -> None:
    await session.execute(update(Clan).where(Clan.id == clan_id).values(owner_id=owner_id))


async def update_profile(
    session: AsyncSession,
    *,
    clan_id: int,
    name: str | None = None,
    description: str | None = None,
    image_path: str | None = _UNSET,
) -> None:
    """image_path не передан (сентинел `_UNSET`) — не трогаем колонку; передан `None` —
    явно очищаем (например, при удалении старой картинки клана)."""
    values: dict = {}
    if name is not None:
        values["name"] = name
    if description is not None:
        values["description"] = description
    if image_path is not _UNSET:
        values["image_path"] = image_path
    if not values:
        return
    await session.execute(update(Clan).where(Clan.id == clan_id).values(**values))


async def get_ubp_season(session: AsyncSession, clan_id: int) -> int:
    """Живая сумма ubp_season участников — см. комментарий в db/models/clan.py."""
    result = await session.execute(
        select(sa_func.coalesce(sa_func.sum(User.ubp_season), 0)).where(User.clan_id == clan_id)
    )
    return result.scalar_one()


async def get_ubp_total(session: AsyncSession, clan_id: int) -> int:
    result = await session.execute(
        select(sa_func.coalesce(sa_func.sum(User.ubp_total), 0)).where(User.clan_id == clan_id)
    )
    return result.scalar_one()


async def list_page(
    session: AsyncSession, *, by_total: bool, limit: int, offset: int
) -> list[tuple[Clan, int, int]]:
    """Клан + живая сумма UBP (сезон или всё время) + число участников, отсортировано по
    убыванию UBP. Постранично через OFFSET — таблица кланов принципиально небольшая
    (ограничена числом кланов, не игроков), так что OFFSET здесь не проблема правила 7."""
    ubp_col = User.ubp_total if by_total else User.ubp_season
    ubp_sum = sa_func.coalesce(sa_func.sum(ubp_col), 0)
    stmt = (
        select(Clan, ubp_sum, sa_func.count(User.id))
        .outerjoin(User, User.clan_id == Clan.id)
        .group_by(Clan.id)
        .order_by(ubp_sum.desc(), Clan.id)
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return [(clan, int(ubp), int(cnt)) for clan, ubp, cnt in result.all()]


async def count_clans(session: AsyncSession) -> int:
    result = await session.execute(select(sa_func.count(Clan.id)))
    return result.scalar_one()


async def list_top_all_time_ids(session: AsyncSession, limit: int = 10) -> set[int]:
    """id кланов из топ-N по UBP за всё время — только им можно ставить картинку клана."""
    ubp_sum = sa_func.coalesce(sa_func.sum(User.ubp_total), 0)
    stmt = (
        select(Clan.id)
        .outerjoin(User, User.clan_id == Clan.id)
        .group_by(Clan.id)
        .order_by(ubp_sum.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return set(result.scalars().all())


# --- ClanMember ---


async def get_member(session: AsyncSession, user_id: int) -> ClanMember | None:
    return await session.get(ClanMember, user_id)


async def list_members(session: AsyncSession, clan_id: int) -> list[ClanMember]:
    result = await session.execute(
        select(ClanMember).where(ClanMember.clan_id == clan_id).order_by(ClanMember.rank, ClanMember.joined_at)
    )
    return list(result.scalars().all())


async def count_members(session: AsyncSession, clan_id: int) -> int:
    result = await session.execute(select(sa_func.count(ClanMember.user_id)).where(ClanMember.clan_id == clan_id))
    return result.scalar_one()


async def add_member(session: AsyncSession, *, clan_id: int, user_id: int, rank: ClanRank) -> bool:
    """Атомарный insert — False, если игрок уже в каком-то клане (PK по user_id, ON
    CONFLICT DO NOTHING). Не коммитит, не трогает users.clan_id — это отдельный шаг
    (см. services/clan), чтобы обе таблицы менялись в одной транзакции."""
    stmt = (
        pg_insert(ClanMember)
        .values(clan_id=clan_id, user_id=user_id, rank=rank)
        .on_conflict_do_nothing(index_elements=[ClanMember.user_id])
        .returning(ClanMember.user_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def remove_member(session: AsyncSession, user_id: int) -> None:
    member = await session.get(ClanMember, user_id)
    if member is not None:
        await session.delete(member)


async def set_rank(session: AsyncSession, *, user_id: int, rank: ClanRank) -> None:
    await session.execute(update(ClanMember).where(ClanMember.user_id == user_id).values(rank=rank))


# --- ClanJoinRequest ---


async def create_join_request(session: AsyncSession, *, clan_id: int, user_id: int, is_invite: bool = False) -> bool:
    """Атомарно — False, если заявка/приглашение уже есть (unique(clan_id, user_id), в
    любом направлении). Не коммитит."""
    stmt = (
        pg_insert(ClanJoinRequest)
        .values(clan_id=clan_id, user_id=user_id, is_invite=is_invite)
        .on_conflict_do_nothing(index_elements=[ClanJoinRequest.clan_id, ClanJoinRequest.user_id])
        .returning(ClanJoinRequest.id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def get_join_request(session: AsyncSession, *, clan_id: int, user_id: int) -> ClanJoinRequest | None:
    result = await session.execute(
        select(ClanJoinRequest).where(ClanJoinRequest.clan_id == clan_id, ClanJoinRequest.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def list_join_requests(session: AsyncSession, clan_id: int) -> list[ClanJoinRequest]:
    result = await session.execute(
        select(ClanJoinRequest).where(ClanJoinRequest.clan_id == clan_id).order_by(ClanJoinRequest.created_at)
    )
    return list(result.scalars().all())


async def get_application_for_user(session: AsyncSession, user_id: int) -> ClanJoinRequest | None:
    """Текущая заявка игрока (is_invite=False) — их одновременно может быть максимум одна
    (см. CLAUDE.md, "Кланы": лимит подтверждён пользователем 2026-08-05, чтобы не плодить
    забытые заявки сразу в кучу кланов). Не путать с list_invites_for_user — входящих
    приглашений от кланов может быть сколько угодно."""
    result = await session.execute(
        select(ClanJoinRequest).where(ClanJoinRequest.user_id == user_id, ClanJoinRequest.is_invite.is_(False))
    )
    return result.scalar_one_or_none()


async def list_invites_for_user(session: AsyncSession, user_id: int) -> list[ClanJoinRequest]:
    """Входящие приглашения от кланов, которые видит сам игрок (чтобы принять/отклонить)."""
    result = await session.execute(
        select(ClanJoinRequest)
        .where(ClanJoinRequest.user_id == user_id, ClanJoinRequest.is_invite.is_(True))
        .order_by(ClanJoinRequest.created_at)
    )
    return list(result.scalars().all())


async def delete_join_request(session: AsyncSession, *, clan_id: int, user_id: int) -> None:
    request = await get_join_request(session, clan_id=clan_id, user_id=user_id)
    if request is not None:
        await session.delete(request)


async def delete_all_join_requests_for_user(session: AsyncSession, user_id: int) -> None:
    """Когда игрок вступил в клан (через заявку или приглашение) — его заявки в ДРУГИЕ
    кланы больше не актуальны."""
    result = await session.execute(select(ClanJoinRequest).where(ClanJoinRequest.user_id == user_id))
    for request in result.scalars().all():
        await session.delete(request)


# --- ClanWar ---


async def get_active_war_for_clan(session: AsyncSession, clan_id: int) -> ClanWar | None:
    result = await session.execute(
        select(ClanWar).where(
            ClanWar.status == ClanWarStatus.active,
            (ClanWar.clan_a_id == clan_id) | (ClanWar.clan_b_id == clan_id),
        )
    )
    return result.scalar_one_or_none()


async def create_war(
    session: AsyncSession, *, clan_a_id: int, clan_b_id: int, ends_at: datetime, ubp_a_start: int, ubp_b_start: int
) -> ClanWar:
    war = ClanWar(
        clan_a_id=clan_a_id,
        clan_b_id=clan_b_id,
        ends_at=ends_at,
        ubp_a_start=ubp_a_start,
        ubp_b_start=ubp_b_start,
    )
    session.add(war)
    await session.flush()
    return war


async def finalize_war(session: AsyncSession, *, war_id: int, winner_clan_id: int | None) -> None:
    await session.execute(
        update(ClanWar)
        .where(ClanWar.id == war_id)
        .values(status=ClanWarStatus.finished, winner_clan_id=winner_clan_id)
    )
