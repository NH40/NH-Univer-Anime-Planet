from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user_id
from api.db import get_session
from api.schemas import UniverseProgressOut
from bot.db.repositories.inventory import get_universe_progress

router = APIRouter(prefix="/api", tags=["progress"])


@router.get("/progress", response_model=list[UniverseProgressOut])
async def get_progress(
    user_id: int = Depends(get_current_user_id), session: AsyncSession = Depends(get_session)
) -> list[UniverseProgressOut]:
    """Тот же % уникальных персонажей по вселенной, что и в Профиле бота (см.
    db.repositories.inventory.get_universe_progress) — единая метрика прогресса что в
    боте, что в Mini App, не две отдельные формулы."""
    progress = await get_universe_progress(session, user_id)
    return [
        UniverseProgressOut(code=p.code, title=p.title, owned=p.owned, total=p.total, percent=p.percent)
        for p in progress
    ]
