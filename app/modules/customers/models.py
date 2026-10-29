from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CustomerAddress(Base):
    __tablename__ = "customer_addresses"
    __table_args__ = (
        Index(
            "uq_customer_address_default_per_user",
            "user_id",
            unique=True,
            sqlite_where=text("is_default = 1"),
            postgresql_where=text("is_default IS TRUE"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(60), nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(160), nullable=False)
    recipient_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    address_line1: Mapped[str] = mapped_column(String(250), nullable=False)
    address_line2: Mapped[str | None] = mapped_column(String(250))
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(120), nullable=False)
    postal_code: Mapped[str | None] = mapped_column(String(24))
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, default="NG")
    delivery_instructions: Mapped[str | None] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
