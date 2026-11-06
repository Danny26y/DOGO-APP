"""record unpaid order cancellations and delivery-agent availability

Revision ID: d0a834e2c951
Revises: f146cbfa2d11
Create Date: 2026-11-06 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d0a834e2c951"
down_revision = "f146cbfa2d11"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("orders", sa.Column("cancellation_reason", sa.String(length=300), nullable=True))
    op.add_column("orders", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "delivery_agents",
        sa.Column("availability_status", sa.String(length=16), server_default=sa.text("'offline'"), nullable=False),
    )
    op.create_index("ix_delivery_agents_availability_status", "delivery_agents", ["availability_status"])


def downgrade():
    op.drop_index("ix_delivery_agents_availability_status", table_name="delivery_agents")
    op.drop_column("delivery_agents", "availability_status")
    op.drop_column("orders", "cancelled_at")
    op.drop_column("orders", "cancellation_reason")
