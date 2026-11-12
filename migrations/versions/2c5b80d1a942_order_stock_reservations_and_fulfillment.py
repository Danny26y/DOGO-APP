"""reserve paid order stock and track merchant fulfillment

Revision ID: 2c5b80d1a942
Revises: 1b8d440ea732
"""

import sqlalchemy as sa
from alembic import op

revision = "2c5b80d1a942"
down_revision = "1b8d440ea732"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("products", sa.Column("reserved_quantity", sa.Integer(), nullable=False, server_default="0"))
    op.create_table(
        "inventory_reservations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_item_id", sa.String(36), sa.ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("order_item_id", name="uq_inventory_reservation_order_item"),
        sa.CheckConstraint("quantity > 0", name="ck_inventory_reservation_positive_quantity"),
    )
    op.create_index("ix_inventory_reservations_order_item_id", "inventory_reservations", ["order_item_id"])
    op.create_index("ix_inventory_reservations_product_id", "inventory_reservations", ["product_id"])
    op.create_index("ix_inventory_reservations_organization_id", "inventory_reservations", ["organization_id"])
    op.create_table(
        "order_fulfillments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("order_id", "organization_id", name="uq_fulfillment_order_merchant"),
    )
    op.create_index("ix_order_fulfillments_order_id", "order_fulfillments", ["order_id"])
    op.create_index("ix_order_fulfillments_organization_id", "order_fulfillments", ["organization_id"])
    op.create_index("ix_order_fulfillments_status", "order_fulfillments", ["status"])


def downgrade():
    op.drop_index("ix_order_fulfillments_status", table_name="order_fulfillments")
    op.drop_index("ix_order_fulfillments_organization_id", table_name="order_fulfillments")
    op.drop_index("ix_order_fulfillments_order_id", table_name="order_fulfillments")
    op.drop_table("order_fulfillments")
    op.drop_index("ix_inventory_reservations_organization_id", table_name="inventory_reservations")
    op.drop_index("ix_inventory_reservations_product_id", table_name="inventory_reservations")
    op.drop_index("ix_inventory_reservations_order_item_id", table_name="inventory_reservations")
    op.drop_table("inventory_reservations")
    op.drop_column("products", "reserved_quantity")
