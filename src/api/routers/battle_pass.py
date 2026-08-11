from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user_id
from api.db import get_session
from api.schemas import (
    BattlePassClaimAllIn,
    BattlePassClaimAllOut,
    BattlePassClaimIn,
    BattlePassClaimOut,
    BattlePassLevelOut,
    BattlePassPageOut,
)
from bot.services import battle_pass as pass_service

router = APIRouter(prefix="/api", tags=["battle_pass"])


@router.get("/battle-pass", response_model=BattlePassPageOut)
async def get_battle_pass_page(
    page: int | None = None,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> BattlePassPageOut:
    """Та же пагинированная лента уровней, что в боте (см. handlers/battle_pass/levels.py) —
    переиспользует services.battle_pass.list_levels напрямую, формула не дублируется.
    page=None (параметр опущен) — открыть сразу на странице с первым незабранным уровнем."""
    page_view = await pass_service.list_levels(session, user_id=user_id, page=page)
    if page_view is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No active season")

    return BattlePassPageOut(
        entries=[
            BattlePassLevelOut(
                level=e.level,
                free_dust=e.free_dust,
                free_tickets=e.free_tickets,
                premium_dust=e.premium_dust,
                premium_tickets=e.premium_tickets,
                premium_coins=e.premium_coins,
                unlocked=e.unlocked,
                free_claimed=e.free_claimed,
                premium_claimed=e.premium_claimed,
            )
            for e in page_view.entries
        ],
        page=page_view.page,
        total_pages=page_view.total_pages,
        current_level=page_view.current_level,
        is_premium=page_view.is_premium,
        progress=page_view.progress,
        level_floor=page_view.level_floor,
        level_ceiling=page_view.level_ceiling,
        claimed_free_level=page_view.claimed_free_level,
        claimed_premium_level=page_view.claimed_premium_level,
    )


@router.post("/battle-pass/claim", response_model=BattlePassClaimOut)
async def claim_battle_pass_level(
    body: BattlePassClaimIn,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> BattlePassClaimOut:
    """Забирает награду ОДНОГО уровня (тап по ячейке в Mini App — см. CLAUDE.md, "Сезонный
    пасс: клейм произвольной ячейки"), вызывает тот же services.battle_pass.claim_level, что
    и бот. Redis-лок на повторный клик не нужен: claim_level уже идемпотентен на уровне БД
    (LevelAlreadyClaimedError вместо двойного начисления)."""
    if body.track not in ("free", "premium"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid track")
    try:
        dust, tickets, coins = await pass_service.claim_level(
            session, user_id=user_id, track=body.track, level=body.level
        )
    except pass_service.NoSeasonActiveError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No active season") from None
    except pass_service.NotPremiumError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Premium not unlocked") from None
    except pass_service.LevelLockedError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Level not unlocked") from None
    except pass_service.LevelAlreadyClaimedError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Already claimed") from None

    return BattlePassClaimOut(dust=dust, tickets=tickets, coins=coins)


@router.post("/battle-pass/claim-all", response_model=BattlePassClaimAllOut)
async def claim_battle_pass_all(
    body: BattlePassClaimAllIn,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> BattlePassClaimAllOut:
    """Забирает разом все незабранные уровни одной ветки — кнопка "Забрать всё" в Mini App."""
    if body.track not in ("free", "premium"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid track")
    try:
        result = await pass_service.claim_all(session, user_id=user_id, track=body.track)
    except pass_service.NoSeasonActiveError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No active season") from None
    except pass_service.NotPremiumError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Premium not unlocked") from None
    except pass_service.NothingToClaimError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nothing to claim") from None

    page = pass_service.page_for_level(result.current_level, current_level=result.current_level)
    return BattlePassClaimAllOut(dust=result.dust, tickets=result.tickets, coins=result.coins, count=result.count, page=page)
