from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.game import SEASON_TOP10_REWARD_COINS
from bot.constant.season import TRANSACTION_REASON_SEASON_TOP_REWARD
from bot.db.models.enums import TransactionCurrency
from bot.db.models.season import Season
from bot.db.models.transaction import Transaction
from bot.db.models.user import User
from bot.db.repositories import season as season_repo
from bot.db.repositories.user import add_coins


class NoActiveSeasonError(Exception):
    pass


@dataclass
class TopPlayerReward:
    user_id: int
    place: int
    ubp_season: int
    coins: int


async def _get_top10(session: AsyncSession) -> list[tuple[int, int]]:
    result = await session.execute(
        select(User.id, User.ubp_season).where(User.ubp_season > 0).order_by(User.ubp_season.desc()).limit(10)
    )
    return result.all()


async def start_new_season(session: AsyncSession, *, version: str) -> tuple[Season, list[TopPlayerReward]]:
    """Завершает текущий активный сезон (если есть): раздаёт коины топ-10 по `ubp_season`
    (`SEASON_TOP10_REWARD_COINS`, подтверждено пользователем 2026-08-05), переносит
    `ubp_season` -> `ubp_total` и обнуляет `ubp_season` у ВСЕХ игроков (сезон закончился
    для всех, не только топ-10), потом создаёт новый активный сезон. Одна логическая
    операция — один commit в конце. UBP клана пересчитывать не нужно — это живая
    агрегация ubp_season игроков (см. CLAUDE.md, "Кланы"), обнуление отразится сразу же."""
    old_season = await season_repo.get_active(session)

    rewards: list[TopPlayerReward] = []
    if old_season is not None:
        top10 = await _get_top10(session)
        for place, (user_id, ubp_season) in enumerate(top10, start=1):
            coins = SEASON_TOP10_REWARD_COINS[place - 1] if place <= len(SEASON_TOP10_REWARD_COINS) else 0
            if coins <= 0:
                continue
            await add_coins(session, user_id=user_id, amount=coins)
            session.add(
                Transaction(
                    user_id=user_id,
                    currency=TransactionCurrency.coins,
                    amount=coins,
                    reason=TRANSACTION_REASON_SEASON_TOP_REWARD,
                )
            )
            rewards.append(TopPlayerReward(user_id=user_id, place=place, ubp_season=ubp_season, coins=coins))

        await session.execute(update(User).values(ubp_total=User.ubp_total + User.ubp_season, ubp_season=0))
        await season_repo.end_active(session, season_id=old_season.id)

    new_season = await season_repo.create(session, version=version)
    await session.commit()
    return new_season, rewards


async def bump_version(session: AsyncSession, *, version: str) -> Season:
    """Смена версии x.x.x БЕЗ смены сезона (без обнуления UBP) — отдельное действие
    от start_new_season, см. TODO Этап 10."""
    season = await season_repo.get_active(session)
    if season is None:
        raise NoActiveSeasonError
    await season_repo.set_version(session, season_id=season.id, version=version)
    await session.commit()
    season.version = version
    return season
