from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user_id
from api.db import get_session
from api.schemas import ProfileOut
from bot.db.repositories.user import get_by_id

router = APIRouter(prefix="/api", tags=["profile"])


@router.get("/me", response_model=ProfileOut)
async def get_me(
    user_id: int = Depends(get_current_user_id), session: AsyncSession = Depends(get_session)
) -> ProfileOut:
    user = await get_by_id(session, user_id)
    if user is None:
        # Игрок открыл Mini App, ни разу не нажав /start боту — такой строки в users ещё нет.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Player not registered — open the bot and press /start first")

    return ProfileOut(
        id=user.id,
        display_name=user.display_name,
        universe_selected=user.universe_selected,
        ubp_season=user.ubp_season,
        ubp_total=user.ubp_total,
        dust=user.dust,
        coins=user.coins,
    )
