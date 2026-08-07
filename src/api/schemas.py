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


class BattlePassClaimIn(BaseModel):
    track: str  # "free" | "premium"


class BattlePassClaimOut(BaseModel):
    dust: int
    tickets: int
    coins: int
