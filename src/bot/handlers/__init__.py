from aiogram import Router

from bot.handlers import (
    admin,
    battle_pass,
    casino,
    clan,
    collection,
    daily_bonus,
    deck,
    donate,
    fallback,
    profile,
    promo,
    quest,
    settings,
    shop,
    start,
)


def get_routers() -> list[Router]:
    return [
        admin.router,
        start.router,
        settings.router,
        profile.router,
        daily_bonus.router,
        quest.router,
        deck.router,
        collection.router,
        shop.router,
        casino.router,
        clan.router,
        battle_pass.router,
        donate.router,
        promo.router,
        # Catch-all — обязан быть последним: ловит апдейты, которые не забрал ни один
        # другой роутер (см. handlers/fallback/fallback.py).
        fallback.router,
    ]
