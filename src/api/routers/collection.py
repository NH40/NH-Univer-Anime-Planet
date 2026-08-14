from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user_id
from api.db import get_session
from api.schemas import CardStackOut, CardStackPageOut
from bot.db.repositories.inventory import (
    OwnedStack,
    list_owned_stacks_in_event_universes_page,
    list_owned_stacks_in_universe_page,
)

router = APIRouter(prefix="/api", tags=["collection"])

# Дефолт совпадает с тем, что описал пользователь (см. CLAUDE.md, "Долгая загрузка карт
# в Mini App") — 20 карт на страницу, дальше подгружается по мере скролла. Верхняя граница
# — защита от абсурдного query-параметра, не игровой баланс.
_DEFAULT_LIMIT = 20
_MAX_LIMIT = 100


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


@router.get("/collection/events", response_model=CardStackPageOut)
async def get_event_collection(
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    search: str | None = None,
    tier: int | None = None,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> CardStackPageOut:
    """Единая категория "Ивенты" — карточки игрока из ВСЕХ вселенных с `is_event=True`
    разом (см. CLAUDE.md, "Ивенты"), не по одному конкретному universe_code. Зарегистрирован
    ВЫШЕ динамического `/collection/{universe_code}` — иначе Starlette матчил бы литерал
    "events" как значение `universe_code` (маршруты проверяются в порядке регистрации).
    Постранично — см. get_collection ниже."""
    stacks, has_more = await list_owned_stacks_in_event_universes_page(
        session, user_id=user_id, offset=offset, limit=limit, search=search, tier=tier
    )
    return CardStackPageOut(items=_stacks_out(stacks), has_more=has_more)


@router.get("/collection/{universe_code}", response_model=CardStackPageOut)
async def get_collection(
    universe_code: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    search: str | None = None,
    tier: int | None = None,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> CardStackPageOut:
    """Коллекция игрока в вселенной, постранично (см. CLAUDE.md, "Долгая загрузка карт в
    Mini App") — фронтенд запрашивает `limit` карт за раз и подгружает следующую порцию по
    мере скролла, вместо того чтобы тянуть всю коллекцию одним ответом. `search`/`tier` —
    те же фильтры, что раньше применялись на уже загруженном массиве на клиенте, теперь в
    SQL, иначе поиск не находил бы карты, которые ещё не подгрузились. Пустая страница для
    чужой/несуществующей вселенной — не 404, чужих данных тут и так нет."""
    stacks, has_more = await list_owned_stacks_in_universe_page(
        session, user_id=user_id, universe_code=universe_code, offset=offset, limit=limit, search=search, tier=tier
    )
    return CardStackPageOut(items=_stacks_out(stacks), has_more=has_more)
