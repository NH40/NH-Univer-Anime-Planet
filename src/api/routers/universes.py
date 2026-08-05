from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user_id
from api.db import get_session
from api.schemas import UniverseOut
from bot.db.repositories.inventory import list_owned_universes

router = APIRouter(prefix="/api", tags=["universes"])


@router.get("/universes", response_model=list[UniverseOut])
async def list_my_universes(
    user_id: int = Depends(get_current_user_id), session: AsyncSession = Depends(get_session)
) -> list[UniverseOut]:
    """Вселенные, где у ИГРОКА есть хотя бы одна карта — не общий список всех активных
    вселенных бота (см. TODO, Этап 12: "список вселенных игрока")."""
    owned = await list_owned_universes(session, user_id)
    return [UniverseOut(code=code, title=title) for code, title in owned]
