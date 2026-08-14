from __future__ import annotations

from pydantic import BaseModel


class ProfileOut(BaseModel):
    id: int
    display_name: str | None
    universe_selected: str | None
    ubp_season: int
    ubp_total: int
    dust: int
    coins: int


class UniverseOut(BaseModel):
    code: str
    title: str


class CardStackOut(BaseModel):
    card_id: int
    external_id: str
    name: str
    description: str | None
    base_ubp: int
    stars: int
    quantity: int
    image_url: str


class CardStackPageOut(BaseModel):
    """Постраничная выдача коллекции (см. CLAUDE.md, "Долгая загрузка карт в Mini App") —
    `items` — одна страница стопок, `has_more` говорит фронтенду, есть ли смысл запрашивать
    следующую (`offset` растёт на len(items) каждый раз, без отдельного COUNT-запроса —
    см. db.repositories.inventory: страница читается limit+1 строкой, лишняя обрезается)."""

    items: list[CardStackOut]
    has_more: bool


class UniverseProgressOut(BaseModel):
    code: str
    title: str
    owned: int
    total: int
    percent: int


class BattlePassLevelOut(BaseModel):
    level: int
    free_dust: int
    free_tickets: int
    premium_dust: int
    premium_tickets: int
    premium_coins: int
    unlocked: bool
    free_claimed: bool
    premium_claimed: bool


class BattlePassPageOut(BaseModel):
    entries: list[BattlePassLevelOut]
    page: int
    total_pages: int
    current_level: int
    is_premium: bool
    progress: int
    level_floor: int
    level_ceiling: int
    claimed_free_level: int
    claimed_premium_level: int


class BattlePassClaimIn(BaseModel):
    track: str  # "free" | "premium"
    level: int


class BattlePassClaimOut(BaseModel):
    dust: int
    tickets: int
    coins: int


class BattlePassClaimAllIn(BaseModel):
    track: str  # "free" | "premium"


class BattlePassClaimAllOut(BaseModel):
    dust: int
    tickets: int
    coins: int
    count: int
    page: int  # страница, на которую фронтенд должен переключиться (см. api/routers/battle_pass.py)
