from __future__ import annotations

import random

from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.card import Card
from bot.db.repositories.card import list_by_universe
from bot.config.game import TIER_CHANCE_PERCENT


class UniverseNotReadyError(Exception):
    """Во вселенной не заполнен один из фиксированных UBP-тиров — по решению пользователя
    (2026-08-03) это считается ошибкой данных, а не поводом перераспределять шанс."""

    def __init__(self, universe_code: str, missing_tiers: list[int]) -> None:
        self.universe_code = universe_code
        self.missing_tiers = missing_tiers
        super().__init__(f"universe '{universe_code}' missing tiers: {missing_tiers}")


async def get_tier_map(session: AsyncSession, universe_code: str) -> dict[int, list[Card]]:
    """Карты вселенной, сгруппированные по каноническим UBP-тирам. Карты с UBP вне
    фиксированного набора (см. game_config.TIER_CHANCE_PERCENT) в крутке не участвуют —
    seed_cards.py должен был предупредить об этом при загрузке датасета."""
    cards = await list_by_universe(session, universe_code)
    tier_map: dict[int, list[Card]] = {tier: [] for tier in TIER_CHANCE_PERCENT}
    for card in cards:
        if card.base_ubp in tier_map:
            tier_map[card.base_ubp].append(card)

    missing = sorted((tier for tier, tier_cards in tier_map.items() if not tier_cards), reverse=True)
    if missing:
        raise UniverseNotReadyError(universe_code, missing)

    return tier_map


def pick_card(tier_map: dict[int, list[Card]]) -> Card:
    """Взвешенный выбор тира, затем равновероятный выбор карты внутри тира."""
    tiers = list(TIER_CHANCE_PERCENT.keys())
    weights = [TIER_CHANCE_PERCENT[tier] for tier in tiers]
    tier = random.choices(tiers, weights=weights, k=1)[0]
    return random.choice(tier_map[tier])
