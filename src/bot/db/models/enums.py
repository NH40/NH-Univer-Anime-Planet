from __future__ import annotations

import enum


class ClanRank(str, enum.Enum):
    owner = "owner"
    deputy = "deputy"
    captain = "captain"
    member = "member"


class ClanWarStatus(str, enum.Enum):
    active = "active"
    finished = "finished"
    cancelled = "cancelled"


class TransactionCurrency(str, enum.Enum):
    dust = "dust"
    coins = "coins"
    ubp_season = "ubp_season"
    tickets = "tickets"


class PromoCodeType(str, enum.Enum):
    uses = "uses"          # ограничено количеством активаций
    time = "time"          # ограничено сроком действия (expires_at)
    user_list = "user_list"  # только перечисленные username


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    succeeded = "succeeded"
    canceled = "canceled"
