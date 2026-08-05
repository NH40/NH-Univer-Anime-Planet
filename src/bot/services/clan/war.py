from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.game import CLAN_WAR_DURATION_HOURS, CLAN_WAR_REWARD_DUST
from bot.constant.clan import TRANSACTION_REASON_WAR_REWARD
from bot.db.models.clan import ClanWar
from bot.db.models.enums import ClanWarStatus, TransactionCurrency
from bot.db.models.transaction import Transaction
from bot.db.repositories import clan as clan_repo
from bot.db.repositories.user import add_dust
from bot.services.clan.clan import MANAGER_RANKS


class NotAuthorizedError(Exception):
    pass


class AlreadyAtWarError(Exception):
    """Один из кланов уже в активной войне (у клана может быть только одна война разом)."""


@dataclass
class WarProgress:
    war: ClanWar
    ubp_a_now: int
    ubp_b_now: int

    @property
    def gained_a(self) -> int:
        return max(0, self.ubp_a_now - self.war.ubp_a_start)

    @property
    def gained_b(self) -> int:
        return max(0, self.ubp_b_now - self.war.ubp_b_start)


async def start_war(session: AsyncSession, *, clan_a_id: int, clan_b_id: int, actor_id: int) -> ClanWar:
    member = await clan_repo.get_member(session, actor_id)
    if member is None or member.clan_id != clan_a_id or member.rank not in MANAGER_RANKS:
        raise NotAuthorizedError

    if await clan_repo.get_active_war_for_clan(session, clan_a_id) is not None:
        raise AlreadyAtWarError
    if await clan_repo.get_active_war_for_clan(session, clan_b_id) is not None:
        raise AlreadyAtWarError

    ubp_a_start = await clan_repo.get_ubp_season(session, clan_a_id)
    ubp_b_start = await clan_repo.get_ubp_season(session, clan_b_id)
    ends_at = datetime.now(timezone.utc) + timedelta(hours=CLAN_WAR_DURATION_HOURS)

    war = await clan_repo.create_war(
        session,
        clan_a_id=clan_a_id,
        clan_b_id=clan_b_id,
        ends_at=ends_at,
        ubp_a_start=ubp_a_start,
        ubp_b_start=ubp_b_start,
    )
    await session.commit()
    return war


async def _reward_winner(session: AsyncSession, winner_clan_id: int) -> None:
    members = await clan_repo.list_members(session, winner_clan_id)
    for member in members:
        await add_dust(session, user_id=member.user_id, amount=CLAN_WAR_REWARD_DUST)
        session.add(
            Transaction(
                user_id=member.user_id,
                currency=TransactionCurrency.dust,
                amount=CLAN_WAR_REWARD_DUST,
                reason=TRANSACTION_REASON_WAR_REWARD,
            )
        )


async def get_progress(session: AsyncSession, war: ClanWar) -> WarProgress:
    """Прогресс войны — живая разница между текущей суммой UBP клана и снимком на старте
    (см. db/models/clan.py). Если война уже должна была закончиться (`ends_at` в прошлом),
    но статус ещё 'active' — финализируем её прямо здесь (лениво, фонового шедулера в
    проекте нет, см. CLAUDE.md)."""
    ubp_a_now = await clan_repo.get_ubp_season(session, war.clan_a_id)
    ubp_b_now = await clan_repo.get_ubp_season(session, war.clan_b_id)

    if war.status == ClanWarStatus.active and datetime.now(timezone.utc) >= war.ends_at:
        gained_a = max(0, ubp_a_now - war.ubp_a_start)
        gained_b = max(0, ubp_b_now - war.ubp_b_start)

        winner_id: int | None = None
        if gained_a > gained_b:
            winner_id = war.clan_a_id
        elif gained_b > gained_a:
            winner_id = war.clan_b_id
        # Ничья — winner_id остаётся None, награда никому не выдаётся.

        if winner_id is not None:
            await _reward_winner(session, winner_id)
        await clan_repo.finalize_war(session, war_id=war.id, winner_clan_id=winner_id)
        await session.commit()
        war.status = ClanWarStatus.finished
        war.winner_clan_id = winner_id

    return WarProgress(war=war, ubp_a_now=ubp_a_now, ubp_b_now=ubp_b_now)
