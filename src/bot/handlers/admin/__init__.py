from aiogram import Router

from bot.filters.admin import IsAdminFilter
from bot.handlers.admin import admin, broadcast, delete_account, mass_grant, promo, referral, season

router = Router(name="admin_root")
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())

router.include_router(admin.router)
router.include_router(season.router)
router.include_router(promo.router)
router.include_router(referral.router)
router.include_router(broadcast.router)
router.include_router(mass_grant.router)
router.include_router(delete_account.router)

__all__ = ["router"]
