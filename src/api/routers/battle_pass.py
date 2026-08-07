from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user_id
from api.db import get_session
from api.schemas import BattlePassClaimIn, BattlePassClaimOut, BattlePassLevelOut, BattlePassPageOut
from bot.services import battle_pass as pass_service

router = APIRouter(prefix="/api", tags=["battle_pass"])


@router.get("/battle-pass", response_model=BattlePassPageOut)
async def get_battle_pass_page(
    page: int = 1,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> BattlePassPageOut:
    """Та же пагинированная лента уровней, что в боте (см. handlers/battle_pass/levels.py) —
    переиспользует services.battle_pass.list_levels напрямую, формула не дублируется."""
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
    )


@router.post("/battle-pass/claim", response_model=BattlePassClaimOut)
async def claim_battle_pass(
    body: BattlePassClaimIn,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> BattlePassClaimOut:
    """Первый write-эндпоинт Mini App (см. CLAUDE.md, "Mini App") — вызывает те же
    services.battle_pass.claim_free/claim_premium, что и бот, без дублирования логики.
    Redis-лок на повторный клик не нужен: claim_* уже идемпотентны на уровне БД
    (high-water mark — повторный вызов просто получает NothingToClaimError, не двойное
    начисление)."""
    try:
        if body.track == "free":
            dust, tickets = await pass_service.claim_free(session, user_id=user_id)
            coins = 0
        elif body.track == "premium":
            dust, tickets, coins = await pass_service.claim_premium(session, user_id=user_id)
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid track")
    except pass_service.NoSeasonActiveError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No active season") from None
    except pass_service.NotPremiumError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Premium not unlocked") from None
    except pass_service.NothingToClaimError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nothing to claim") from None

    return BattlePassClaimOut(dust=dust, tickets=tickets, coins=coins)
