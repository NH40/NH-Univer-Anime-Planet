from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from bot.db.base import Base
from bot.db.models.enums import ClanRank, ClanWarStatus

MAX_CLAN_MEMBERS = 15


class Clan(Base):
    """UBP клана (за сезон/всего) намеренно не хранится отдельной колонкой — это живая
    сумма `ubp_season`/`ubp_total` всех участников (`SELECT SUM(...) FROM users WHERE
    clan_id = ...`, индекс `ix_users_clan_id` уже есть). Хранить как денормализованный
    счётчик означало бы обновлять его при КАЖДОМ начислении UBP игроку (роль/слияние),
    завязывая gacha/merge на существование клана — при максимум 15 участниках на клан
    live-агрегация дешевле и не создаёт этой связки."""

    __tablename__ = "clans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))

    # Заготовка под будущую механику — не реализуем сейчас (см. TODO, Этап 7).
    level: Mapped[int] = mapped_column(Integer, default=1, server_default="1")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ClanMember(Base):
    """Игрок состоит максимум в одном клане — поэтому user_id и есть PK."""

    __tablename__ = "clan_members"
    __table_args__ = (
        Index("ix_clan_members_clan_id", "clan_id"),
        # Максимум один owner и один deputy НА КЛАН — атомарная гарантия на уровне БД,
        # а не только проверка в Python (которая могла бы гонку пропустить).
        Index(
            "uq_clan_members_clan_id_owner_deputy",
            "clan_id",
            "rank",
            unique=True,
            postgresql_where="rank IN ('owner', 'deputy')",
        ),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    clan_id: Mapped[int] = mapped_column(ForeignKey("clans.id", ondelete="CASCADE"))
    rank: Mapped[ClanRank] = mapped_column(Enum(ClanRank, name="clan_rank"), default=ClanRank.member)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ClanJoinRequest(Base):
    """Одна и та же таблица для заявок игрока в клан И приглашений клана игроку —
    направление отличает `is_invite`. Кто должен подтверждать, зависит от направления:
    заявку игрока принимает владелец/зам клана, приглашение клана принимает сам игрок
    (см. services/clan) — иначе клан мог бы силой добавлять к себе не спросив согласия."""

    __tablename__ = "clan_join_requests"
    __table_args__ = (UniqueConstraint("clan_id", "user_id", name="uq_clan_join_requests_clan_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    clan_id: Mapped[int] = mapped_column(ForeignKey("clans.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    is_invite: Mapped[bool] = mapped_column(default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ClanWar(Base):
    """Прогресс войны — это НЕ отдельный счётчик, который надо инкрементить при каждом
    начислении UBP (см. комментарий в Clan) — он считается как разница между текущей
    live-суммой UBP клана и снимком на момент старта войны (`ubp_a_start`/`ubp_b_start`).
    Война не завершается фоновой задачей (в проекте пока нет шедулера) — статус проверяется
    и финализируется лениво: при следующем обращении к войне после `ends_at`."""

    __tablename__ = "clan_wars"
    __table_args__ = (Index("ix_clan_wars_status", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    clan_a_id: Mapped[int] = mapped_column(ForeignKey("clans.id", ondelete="CASCADE"))
    clan_b_id: Mapped[int] = mapped_column(ForeignKey("clans.id", ondelete="CASCADE"))

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    ubp_a_start: Mapped[int] = mapped_column(BigInteger)
    ubp_b_start: Mapped[int] = mapped_column(BigInteger)

    status: Mapped[ClanWarStatus] = mapped_column(
        Enum(ClanWarStatus, name="clan_war_status"), default=ClanWarStatus.active
    )
    winner_clan_id: Mapped[int | None] = mapped_column(
        ForeignKey("clans.id", ondelete="SET NULL"), nullable=True
    )
