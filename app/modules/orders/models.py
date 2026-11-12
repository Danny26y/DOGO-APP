from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    customer_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)
    items: Mapped[list["CartItem"]] = relationship(back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("cart_id", "product_id", name="uq_cart_product"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    cart_id: Mapped[str] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), index=True, nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    cart: Mapped[Cart] = relationship(back_populates="items")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("customer_user_id", "idempotency_key", name="uq_order_customer_idempotency"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    customer_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="awaiting_payment", index=True)
    payment_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    subtotal_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    delivery_address_id: Mapped[str | None] = mapped_column(String(36))
    delivery_address_snapshot: Mapped[dict | None] = mapped_column(JSON)
    cancellation_reason: Mapped[str | None] = mapped_column(String(300))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), nullable=False)
    merchant_organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    product_title: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    line_total_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    order: Mapped[Order] = relationship(back_populates="items")


class InventoryReservation(Base):
    __tablename__ = "inventory_reservations"
    __table_args__ = (
        UniqueConstraint("order_item_id", name="uq_inventory_reservation_order_item"),
        CheckConstraint("quantity > 0", name="ck_inventory_reservation_positive_quantity"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    order_item_id: Mapped[str] = mapped_column(ForeignKey("order_items.id", ondelete="CASCADE"), index=True, nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True, nullable=False)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="reserved")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class OrderFulfillment(Base):
    __tablename__ = "order_fulfillments"
    __table_args__ = (UniqueConstraint("order_id", "organization_id", name="uq_fulfillment_order_merchant"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)
