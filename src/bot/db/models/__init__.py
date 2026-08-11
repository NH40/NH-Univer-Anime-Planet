"""Импортировать все модели здесь, чтобы Base.metadata видел их (нужно для Alembic autogenerate)."""

from bot.db.models.battle_pass import BattlePass
from bot.db.models.battle_pass_claim import BattlePassClaim
from bot.db.models.card import Card
from bot.db.models.clan import Clan, ClanJoinRequest, ClanMember, ClanWar
from bot.db.models.event import Event
from bot.db.models.inventory import UserCard
from bot.db.models.payment import Payment
from bot.db.models.promocode import PromoCode, PromoRedemption
from bot.db.models.quest import DailyQuest
from bot.db.models.referral import ReferralLink, ReferralVisit
from bot.db.models.season import Season
from bot.db.models.transaction import Transaction
from bot.db.models.universe import Universe
from bot.db.models.user import User

__all__ = [
    "BattlePass",
    "BattlePassClaim",
    "Card",
    "Clan",
    "ClanJoinRequest",
    "ClanMember",
    "ClanWar",
    "DailyQuest",
    "Event",
    "UserCard",
    "Payment",
    "PromoCode",
    "PromoRedemption",
    "ReferralLink",
    "ReferralVisit",
    "Season",
    "Transaction",
    "Universe",
    "User",
]
