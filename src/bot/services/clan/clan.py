from __future__ import annotations

import math
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.game import CLAN_TOP_IMAGE_ELIGIBLE_COUNT
from bot.db.models.clan import MAX_CLAN_MEMBERS, Clan, ClanMember
from bot.db.models.enums import ClanRank
from bot.db.repositories import clan as clan_repo
from bot.db.repositories.user import get_many_by_ids, set_clan


class ClanNameTakenError(Exception):
    pass


class AlreadyInClanError(Exception):
    pass


class NotInClanError(Exception):
    pass


class ClanNotFoundError(Exception):
    pass


class ClanFullError(Exception):
    pass


class RequestNotFoundError(Exception):
    pass


class NotAuthorizedError(Exception):
    """Действие требует ранга владельца/зама, а актор им не является."""


class MustTransferOwnershipFirstError(Exception):
    """Владелец не может просто выйти — сначала должен передать клан кому-то ещё."""


class AlreadyAppliedElsewhereError(Exception):
    """У игрока уже есть активная заявка в ДРУГОЙ клан — заявка разрешена одновременно
    только в один клан (подтверждено пользователем 2026-08-05), чтобы не плодить забытые
    "висящие" заявки сразу в куче кланов. Заявку в тот же клан — не ошибка, no-op."""


MANAGER_RANKS = (ClanRank.owner, ClanRank.deputy)


@dataclass
class ClanView:
    clan: Clan
    ubp_season: int
    ubp_total: int
    member_count: int
    is_top10_all_time: bool


async def _require_manager(session: AsyncSession, *, clan_id: int, actor_id: int) -> ClanMember:
    member = await clan_repo.get_member(session, actor_id)
    if member is None or member.clan_id != clan_id or member.rank not in MANAGER_RANKS:
        raise NotAuthorizedError
    return member


async def create_clan(session: AsyncSession, *, name: str, owner_id: int) -> Clan:
    """Одна логическая операция — клан + запись владельца в участники + users.clan_id
    случаются вместе или не случаются вовсе (см. CLAUDE.md, правило 10)."""
    if await clan_repo.get_member(session, owner_id) is not None:
        raise AlreadyInClanError

    clan = await clan_repo.create(session, name=name, owner_id=owner_id)
    if clan is None:
        raise ClanNameTakenError

    ok = await clan_repo.add_member(session, clan_id=clan.id, user_id=owner_id, rank=ClanRank.owner)
    if not ok:
        # Гонка: кто-то успел вступить в другой клан между проверкой выше и этим insert.
        # Ничего не коммитим — весь insert клана тоже откатится при закрытии сессии.
        raise AlreadyInClanError

    await set_clan(session, user_id=owner_id, clan_id=clan.id)
    await session.commit()
    return clan


async def get_clan_view(session: AsyncSession, clan_id: int) -> ClanView | None:
    clan = await clan_repo.get_by_id(session, clan_id)
    if clan is None:
        return None
    ubp_season = await clan_repo.get_ubp_season(session, clan_id)
    ubp_total = await clan_repo.get_ubp_total(session, clan_id)
    member_count = await clan_repo.count_members(session, clan_id)
    top_ids = await clan_repo.list_top_all_time_ids(session, limit=CLAN_TOP_IMAGE_ELIGIBLE_COUNT)
    return ClanView(
        clan=clan,
        ubp_season=ubp_season,
        ubp_total=ubp_total,
        member_count=member_count,
        is_top10_all_time=clan_id in top_ids,
    )


async def browse_clans(
    session: AsyncSession, *, by_total: bool, page: int, page_size: int
) -> tuple[list[tuple[Clan, int, int]], int]:
    total = await clan_repo.count_clans(session)
    total_pages = max(1, math.ceil(total / page_size))
    page = max(0, min(page, total_pages - 1))
    rows = await clan_repo.list_page(session, by_total=by_total, limit=page_size, offset=page * page_size)
    return rows, total_pages


async def apply_to_clan(session: AsyncSession, *, clan_id: int, user_id: int) -> None:
    """Заявка разрешена только в ОДИН клан одновременно (см. AlreadyAppliedElsewhereError) —
    защита от гонки та же, что и у остальных resource-affecting действий: колбэк на кнопке
    "Подать заявку" держит Redis-лок по user_id (не по паре user_id+clan_id), поэтому две
    заявки в разные кланы от одного игрока не могут выполниться конкурентно (см.
    handlers/clan: LOCK_ACTION_APPLY_CLAN)."""
    if await clan_repo.get_member(session, user_id) is not None:
        raise AlreadyInClanError
    if await clan_repo.get_by_id(session, clan_id) is None:
        raise ClanNotFoundError

    existing = await clan_repo.get_application_for_user(session, user_id)
    if existing is not None and existing.clan_id != clan_id:
        raise AlreadyAppliedElsewhereError

    ok = await clan_repo.create_join_request(session, clan_id=clan_id, user_id=user_id, is_invite=False)
    await session.commit()
    if not ok:
        # Заявка (или приглашение от этого же клана) уже есть — не ошибка, просто no-op.
        return


async def cancel_application(session: AsyncSession, *, clan_id: int, user_id: int) -> None:
    await clan_repo.delete_join_request(session, clan_id=clan_id, user_id=user_id)
    await session.commit()


async def list_applications(session: AsyncSession, clan_id: int) -> list:
    requests = await clan_repo.list_join_requests(session, clan_id)
    return [r for r in requests if not r.is_invite]


async def list_outgoing_invites(session: AsyncSession, clan_id: int) -> list:
    requests = await clan_repo.list_join_requests(session, clan_id)
    return [r for r in requests if r.is_invite]


async def _finalize_join(session: AsyncSession, *, clan_id: int, user_id: int, rank: ClanRank) -> None:
    """Общий хвост accept_application/accept_invite: добавить в участники, проставить
    clan_id игроку, убрать все его заявки/приглашения (в этот клан и другие — если
    он подал заявки в несколько кланов одновременно, они больше не актуальны)."""
    if await clan_repo.count_members(session, clan_id) >= MAX_CLAN_MEMBERS:
        raise ClanFullError
    if await clan_repo.get_member(session, user_id) is not None:
        raise AlreadyInClanError

    ok = await clan_repo.add_member(session, clan_id=clan_id, user_id=user_id, rank=rank)
    if not ok:
        raise AlreadyInClanError

    await set_clan(session, user_id=user_id, clan_id=clan_id)
    await clan_repo.delete_all_join_requests_for_user(session, user_id)
    await session.commit()


async def accept_application(session: AsyncSession, *, clan_id: int, user_id: int, actor_id: int) -> None:
    await _require_manager(session, clan_id=clan_id, actor_id=actor_id)
    request = await clan_repo.get_join_request(session, clan_id=clan_id, user_id=user_id)
    if request is None or request.is_invite:
        raise RequestNotFoundError
    await _finalize_join(session, clan_id=clan_id, user_id=user_id, rank=ClanRank.member)


async def reject_application(session: AsyncSession, *, clan_id: int, user_id: int, actor_id: int) -> None:
    await _require_manager(session, clan_id=clan_id, actor_id=actor_id)
    await clan_repo.delete_join_request(session, clan_id=clan_id, user_id=user_id)
    await session.commit()


async def invite_player(session: AsyncSession, *, clan_id: int, target_user_id: int, actor_id: int) -> bool:
    await _require_manager(session, clan_id=clan_id, actor_id=actor_id)
    if await clan_repo.get_member(session, target_user_id) is not None:
        raise AlreadyInClanError
    ok = await clan_repo.create_join_request(session, clan_id=clan_id, user_id=target_user_id, is_invite=True)
    await session.commit()
    return ok


async def accept_invite(session: AsyncSession, *, clan_id: int, user_id: int) -> None:
    request = await clan_repo.get_join_request(session, clan_id=clan_id, user_id=user_id)
    if request is None or not request.is_invite:
        raise RequestNotFoundError
    await _finalize_join(session, clan_id=clan_id, user_id=user_id, rank=ClanRank.member)


async def decline_invite(session: AsyncSession, *, clan_id: int, user_id: int) -> None:
    await clan_repo.delete_join_request(session, clan_id=clan_id, user_id=user_id)
    await session.commit()


async def list_members_with_users(session: AsyncSession, clan_id: int):
    members = await clan_repo.list_members(session, clan_id)
    users = await get_many_by_ids(session, [m.user_id for m in members])
    return [(m, users[m.user_id]) for m in members if m.user_id in users]


async def set_member_rank(
    session: AsyncSession, *, clan_id: int, actor_id: int, target_user_id: int, new_rank: ClanRank
) -> None:
    """Ранги распределяет только владелец (см. CLAUDE.md/TODO — в исходном описании это
    прямо сказано про владельца, не зама). owner/member через эту функцию не назначить —
    owner меняется только через transfer_ownership, а member — это ранг "по умолчанию",
    условно можно понизить кого угодно до member, но НЕ повысить кого-то в owner тут."""
    member = await clan_repo.get_member(session, actor_id)
    if member is None or member.clan_id != clan_id or member.rank != ClanRank.owner:
        raise NotAuthorizedError
    if new_rank == ClanRank.owner:
        raise NotAuthorizedError

    target = await clan_repo.get_member(session, target_user_id)
    if target is None or target.clan_id != clan_id:
        raise NotInClanError

    await clan_repo.set_rank(session, user_id=target_user_id, rank=new_rank)
    await session.commit()


async def transfer_ownership(session: AsyncSession, *, clan_id: int, current_owner_id: int, new_owner_id: int) -> None:
    owner_member = await clan_repo.get_member(session, current_owner_id)
    if owner_member is None or owner_member.clan_id != clan_id or owner_member.rank != ClanRank.owner:
        raise NotAuthorizedError

    new_owner_member = await clan_repo.get_member(session, new_owner_id)
    if new_owner_member is None or new_owner_member.clan_id != clan_id:
        raise NotInClanError

    # Порядок важен: сначала снять owner (освобождает слот в частичном уникальном индексе
    # (clan_id, rank) WHERE rank IN ('owner','deputy')), потом назначить нового — иначе
    # второй UPDATE упадёт на констрейнте (см. db/models/clan.py).
    await clan_repo.set_rank(session, user_id=current_owner_id, rank=ClanRank.member)
    await clan_repo.set_rank(session, user_id=new_owner_id, rank=ClanRank.owner)
    await clan_repo.set_owner(session, clan_id=clan_id, owner_id=new_owner_id)
    await session.commit()


async def edit_profile(
    session: AsyncSession,
    *,
    clan_id: int,
    actor_id: int,
    name: str | None = None,
    description: str | None = None,
) -> None:
    await _require_manager(session, clan_id=clan_id, actor_id=actor_id)
    if name is not None:
        existing = await clan_repo.get_by_id(session, clan_id)
        if existing is None:
            raise ClanNotFoundError
    try:
        await clan_repo.update_profile(session, clan_id=clan_id, name=name, description=description)
        await session.commit()
    except IntegrityError:
        # UPDATE, в отличие от create()'s ON CONFLICT DO NOTHING, не может атомарно вернуть
        # "занято" — ловим уникальный констрейнт по имени постфактум и откатываем.
        await session.rollback()
        raise ClanNameTakenError from None


async def set_image(session: AsyncSession, *, clan_id: int, actor_id: int, image_path: str | None) -> None:
    """Картинку можно ставить/менять только кланам из топ-10 по UBP за всё время (см.
    исходное ТЗ). Проверка здесь, а не только в UI — иначе прямой вызов сервиса в обход
    хендлера мог бы обойти ограничение."""
    await _require_manager(session, clan_id=clan_id, actor_id=actor_id)
    top_ids = await clan_repo.list_top_all_time_ids(session, limit=CLAN_TOP_IMAGE_ELIGIBLE_COUNT)
    if clan_id not in top_ids:
        raise NotAuthorizedError
    await clan_repo.update_profile(session, clan_id=clan_id, image_path=image_path)
    await session.commit()


async def leave_clan(session: AsyncSession, *, user_id: int) -> None:
    member = await clan_repo.get_member(session, user_id)
    if member is None:
        raise NotInClanError
    if member.rank == ClanRank.owner:
        raise MustTransferOwnershipFirstError

    await clan_repo.remove_member(session, user_id)
    await set_clan(session, user_id=user_id, clan_id=None)
    await session.commit()
