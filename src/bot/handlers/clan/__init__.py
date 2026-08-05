from aiogram import Router

from bot.handlers.clan import clan, edit, exchange, ranks, requests, topclan, war

router = Router(name="clan_root")
router.include_router(clan.router)
router.include_router(requests.router)
router.include_router(ranks.router)
router.include_router(edit.router)
router.include_router(exchange.router)
router.include_router(war.router)
router.include_router(topclan.router)

__all__ = ["router"]
