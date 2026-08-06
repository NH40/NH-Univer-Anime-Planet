from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user_id
from api.db import get_session
from api.schemas import CardStackOut
from bot.db.repositories.inventory import OwnedStack, list_owned_stacks_in_event_universes, list_owned_stacks_in_universe

router = APIRouter(prefix="/api", tags=["collection"])


def _stacks_out(stacks: list[OwnedStack]) -> list[CardStackOut]:
    return [
        CardStackOut(
            card_id=stack.card.id,
            external_id=stack.card.external_id,
            name=stack.card.name,
            description=stack.card.description,
            base_ubp=stack.card.base_ubp,
            stars=stack.stars,
            quantity=stack.quantity,
            image_url=f"/cards/{stack.card.image_path}",
        )
        for stack in stacks
    ]


@router.get("/collection/events", response_model=list[CardStackOut])
async def get_event_collection(
    user_id: int = Depends(get_current_user_id), session: AsyncSession = Depends(get_session)
) -> list[CardStackOut]:
    """Единая категория "Ивенты" — карточки игрока из ВСЕХ вселенных с `is_event=True`
    разом (см. CLAUDE.md, "Ивенты"), не по одному конкретному universe_code. Зарегистрирован
    ВЫШЕ динамического `/collection/{universe_code}` — иначе Starlette матчил бы литерал
    "events" как значение `universe_code` (маршруты проверяются в порядке регистрации)."""
    stacks = await list_owned_stacks_in_event_universes(session, user_id)
    return _stacks_out(stacks)


@router.get("/collection/{universe_code}", response_model=list[CardStackOut])
async def get_collection(
    universe_code: str,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> list[CardStackOut]:
    """Вся коллекция игрока в вселенной разом (не постранично по тирам, как в боте —
    здесь фронтенд сам решает, как группировать/фильтровать по UBP/звёздам). Пустой
    список для чужой/несуществующей вселенной — не 404, чужих данных тут и так нет."""
    stacks = await list_owned_stacks_in_universe(session, user_id=user_id, universe_code=universe_code)
    return _stacks_out(stacks)
