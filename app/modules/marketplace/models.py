from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProductCategory(Base):
    __tablename__ = "product_categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)


class MerchantStoreProfile(Base):
    __tablename__ = "merchant_store_profiles"

    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True)
    storefront_slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    support_email: Mapped[str | None] = mapped_column(String(320))
    support_phone: Mapped[str | None] = mapped_column(String(32))
    website_url: Mapped[str | None] = mapped_column(String(500))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    category_id: Mapped[str] = mapped_column(ForeignKey("product_categories.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="NGN")
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    length_cm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    width_cm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False)
    quantity_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
