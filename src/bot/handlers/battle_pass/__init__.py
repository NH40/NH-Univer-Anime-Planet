from aiogram import Router

from bot.handlers.battle_pass import battle_pass, levels

router = Router(name="battle_pass_root")
router.include_router(battle_pass.router)
router.include_router(levels.router)

__all__ = ["router"]
