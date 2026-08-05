from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.clan import Clan
from bot.db.models.enums import ClanRank
from bot.db.models.user import User
from bot.db.repositories import clan as clan_repo


class OwnerBlockedError(Exception):
    """Игрок — владелец клана с ДРУГИМИ участниками. Clan.owner_id имеет ondelete=RESTRICT
    (см. db/models/clan.py) — удалить аккаунт нельзя, пока владение не передано (через
    обычный флоу клана — админ не может принудительно передать клан за игрока, это не
    реализовано, см. TODO Этап 10)."""

    def __init__(self, clan_name: str) -> None:
        self.clan_name = clan_name


async def delete_account(session: AsyncSession, *, user_id: int) -> None:
    """Полное удаление аккаунта. Почти все таблицы каскадируются через FK ondelete=CASCADE
    (карточки, транзакции, платежи, промо-активации, рефералы, кланы-участие) — единственное
    исключение Clan.owner_id (RESTRICT). Если игрок — владелец клана: с другими участниками
    внутри — блокируем (см. OwnerBlockedError); единственный участник — клан удаляется вместе
    с ним (каскадом снимутся clan_members/join_requests/wars). Одна операция — один commit."""
    member = await clan_repo.get_member(session, user_id)
    if member is not None and member.rank == ClanRank.owner:
        members = await clan_repo.list_members(session, member.clan_id)
        others = [m for m in members if m.user_id != user_id]
        if others:
            clan = await clan_repo.get_by_id(session, member.clan_id)
            raise OwnerBlockedError(clan_name=clan.name if clan else "")
        await session.execute(delete(Clan).where(Clan.id == member.clan_id))

    await session.execute(delete(User).where(User.id == user_id))
    await session.commit()
