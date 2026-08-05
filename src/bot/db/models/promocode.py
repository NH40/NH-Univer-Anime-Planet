from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    ARRAY,
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from bot.db.base import Base
from bot.db.models.enums import PromoCodeType


class PromoCode(Base):
    __tablename__ = "promo_codes"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    type: Mapped[PromoCodeType] = mapped_column(Enum(PromoCodeType, name="promo_code_type"))

    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    allowed_usernames: Mapped[list[str] | None] = mapped_column(ARRAY(String(32)), nullable=True)

    # {"dust": 100, "coins": 0, "tickets": 0, "cards": [...]}
    reward: Mapped[dict] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PromoRedemption(Base):
    __tablename__ = "promo_redemptions"
    __table_args__ = (UniqueConstraint("promo_code", "user_id", name="uq_promo_redemptions_code_user"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    promo_code: Mapped[str] = mapped_column(ForeignKey("promo_codes.code", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
