from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.game import SEASON_TOP10_REWARD_COINS
from bot.constant.season import TRANSACTION_REASON_SEASON_TOP_REWARD
from bot.db.models.enums import TransactionCurrency
from bot.db.models.season import Season
from bot.db.models.transaction import Transaction
from bot.db.models.user import User
from bot.db.repositories import season as season_repo
from bot.db.repositories import universe_ubp as universe_ubp_repo
from bot.db.repositories.universe import list_active as list_active_universes
from bot.db.repositories.user import add_coins


class NoActiveSeasonError(Exception):
    pass


@dataclass
class TopPlayerReward:
    user_id: int
    place: int
    ubp_season: int
    coins: int
    universe_code: str
    universe_title: str


async def start_new_season(session: AsyncSession, *, version: str) -> tuple[Season, list[TopPlayerReward]]:
    """Завершает текущий активный сезон (если есть): раздаёт коины топ-10 ПО КАЖДОЙ активной
    вселенной ОТДЕЛЬНО (`SEASON_TOP10_REWARD_COINS`, та же таблица на каждую — см. CLAUDE.md,
    "Топ по вселенной", изменено 2026-09-15; раньше был один общий топ-10 по всем вселенным
    разом, подтверждено пользователем 2026-08-05), переносит и `User.ubp_season` -> `ubp_total`,
    и `UserUniverseUbp.ubp_season` -> `ubp_total` для ВСЕХ игроков (сезон закончился для всех,
    не только топ-10), потом создаёт новый активный сезон. Одна логическая операция — один
    commit в конце. UBP клана пересчитывать не нужно — это живая агрегация ubp_season игроков
    (см. CLAUDE.md, "Кланы"), обнуление отразится сразу же."""
    old_season = await season_repo.get_active(session)

    rewards: list[TopPlayerReward] = []
    if old_season is not None:
        for universe in await list_active_universes(session):
            top10 = await universe_ubp_repo.list_season_rows_for_reset(session, universe_code=universe.code, limit=10)
            for place, row in enumerate(top10, start=1):
                coins = SEASON_TOP10_REWARD_COINS[place - 1] if place <= len(SEASON_TOP10_REWARD_COINS) else 0
                if coins <= 0:
                    continue
                await add_coins(session, user_id=row.user_id, amount=coins)
                session.add(
                    Transaction(
                        user_id=row.user_id,
                        currency=TransactionCurrency.coins,
                        amount=coins,
                        reason=TRANSACTION_REASON_SEASON_TOP_REWARD,
                    )
                )
                rewards.append(
                    TopPlayerReward(
                        user_id=row.user_id,
                        place=place,
                        ubp_season=row.ubp,
                        coins=coins,
                        universe_code=universe.code,
                        universe_title=universe.title,
                    )
                )

        await session.execute(update(User).values(ubp_total=User.ubp_total + User.ubp_season, ubp_season=0))
        await universe_ubp_repo.transfer_season_to_total(session)
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
