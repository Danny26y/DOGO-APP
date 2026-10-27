from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow():
    return datetime.now(UTC)


class Shipment(Base):
    __tablename__ = "shipments"
    __table_args__ = (UniqueConstraint("tracking_number", name="uq_shipment_tracking_number"), UniqueConstraint("waybill_number", name="uq_shipment_waybill_number"), UniqueConstraint("quote_id", name="uq_shipment_quote"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    quote_id: Mapped[str] = mapped_column(ForeignKey("pricing_quotes.id"), nullable=False)
    tracking_number: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    waybill_number: Mapped[str] = mapped_column(String(48), nullable=False)
    qr_verification_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    origin_zone: Mapped[str] = mapped_column(String(120), nullable=False)
    destination_zone: Mapped[str] = mapped_column(String(120), nullable=False)
    delivery_tier: Mapped[str] = mapped_column(String(40), nullable=False)
    package_weight_kg: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    pickup_address: Mapped[str] = mapped_column(String(500), nullable=False)
    destination_address: Mapped[str] = mapped_column(String(500), nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(160), nullable=False)
    recipient_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    package_category: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="requested", index=True)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    events: Mapped[list["ShipmentEvent"]] = relationship(back_populates="shipment", cascade="all, delete-orphan", order_by="ShipmentEvent.created_at")


class ShipmentEvent(Base):
    __tablename__ = "shipment_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    shipment_id: Mapped[str] = mapped_column(ForeignKey("shipments.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str | None] = mapped_column(String(500))
    proof_method: Mapped[str | None] = mapped_column(String(32))
    proof_reference: Mapped[str | None] = mapped_column(String(500))
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    shipment: Mapped[Shipment] = relationship(back_populates="events")
