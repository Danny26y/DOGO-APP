"""snapshot the chosen delivery address on orders

Revision ID: c8d5f2490b63
Revises: b2e74f10a6c1
Create Date: 2026-10-29 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c8d5f2490b63"
down_revision = "b2e74f10a6c1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("orders", sa.Column("delivery_address_id", sa.String(length=36), nullable=True))
    op.add_column("orders", sa.Column("delivery_address_snapshot", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("orders", "delivery_address_snapshot")
    op.drop_column("orders", "delivery_address_id")
