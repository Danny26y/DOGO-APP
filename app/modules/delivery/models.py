from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.modules.auth.models import User
    from app.modules.shipments.models import Shipment


def utcnow():
    return datetime.now(UTC)


class DeliveryAgent(Base):
    __tablename__ = "delivery_agents"
    __table_args__ = (UniqueConstraint("user_id", "agent_type", name="uq_delivery_agent_user_type"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    agent_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    user: Mapped["User"] = relationship()


class ShipmentAssignment(Base):
    __tablename__ = "shipment_assignments"
    __table_args__ = (
        Index(
            "uq_current_shipment_assignment_type",
            "shipment_id",
            "agent_type",
            unique=True,
            sqlite_where=text("is_current = 1"),
            postgresql_where=text("is_current IS TRUE"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    shipment_id: Mapped[str] = mapped_column(ForeignKey("shipments.id", ondelete="CASCADE"), index=True, nullable=False)
    delivery_agent_id: Mapped[str] = mapped_column(ForeignKey("delivery_agents.id"), index=True, nullable=False)
    agent_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="assigned", index=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    assigned_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    response_note: Mapped[str | None] = mapped_column(String(300))
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shipment: Mapped["Shipment"] = relationship()
    delivery_agent: Mapped[DeliveryAgent] = relationship()
