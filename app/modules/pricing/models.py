from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow():
    return datetime.now(UTC)


class PricingRule(Base):
    __tablename__ = "pricing_rules"
    __table_args__ = (UniqueConstraint("origin_zone", "destination_zone", "delivery_tier", name="uq_pricing_zone_pair_tier"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    origin_zone: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    destination_zone: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    delivery_tier: Mapped[str] = mapped_column(String(40), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="NGN")
    base_fare_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    per_kg_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class PricingQuote(Base):
    __tablename__ = "pricing_quotes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    pricing_rule_id: Mapped[str] = mapped_column(ForeignKey("pricing_rules.id"), nullable=False)
    origin_zone: Mapped[str] = mapped_column(String(120), nullable=False)
    destination_zone: Mapped[str] = mapped_column(String(120), nullable=False)
    delivery_tier: Mapped[str] = mapped_column(String(40), nullable=False)
    package_weight_kg: Mapped[float] = mapped_column(Numeric(8, 3), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
