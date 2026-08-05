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
    base_ubp: int
    stars: int
    quantity: int
    image_url: str
