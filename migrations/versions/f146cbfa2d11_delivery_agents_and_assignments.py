"""delivery agent profiles and shipment assignments

Revision ID: f146cbfa2d11
Revises: c8d5f2490b63
Create Date: 2026-10-29 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f146cbfa2d11"
down_revision = "c8d5f2490b63"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "delivery_agents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("agent_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "agent_type", name="uq_delivery_agent_user_type"),
    )
    op.create_index("ix_delivery_agents_user_id", "delivery_agents", ["user_id"])
    op.create_index("ix_delivery_agents_agent_type", "delivery_agents", ["agent_type"])
    op.create_index("ix_delivery_agents_status", "delivery_agents", ["status"])
    op.create_table(
        "shipment_assignments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("shipment_id", sa.String(length=36), nullable=False),
        sa.Column("delivery_agent_id", sa.String(length=36), nullable=False),
        sa.Column("agent_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("assigned_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("response_note", sa.String(length=300), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assigned_by_user_id"], ["users.id"], ),
        sa.ForeignKeyConstraint(["delivery_agent_id"], ["delivery_agents.id"], ),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shipment_assignments_shipment_id", "shipment_assignments", ["shipment_id"])
    op.create_index("ix_shipment_assignments_delivery_agent_id", "shipment_assignments", ["delivery_agent_id"])
    op.create_index("ix_shipment_assignments_status", "shipment_assignments", ["status"])
    op.create_index(
        "uq_current_shipment_assignment_type",
        "shipment_assignments",
        ["shipment_id", "agent_type"],
        unique=True,
        sqlite_where=sa.text("is_current = 1"),
        postgresql_where=sa.text("is_current IS TRUE"),
    )


def downgrade():
    op.drop_index("uq_current_shipment_assignment_type", table_name="shipment_assignments")
    op.drop_index("ix_shipment_assignments_status", table_name="shipment_assignments")
    op.drop_index("ix_shipment_assignments_delivery_agent_id", table_name="shipment_assignments")
    op.drop_index("ix_shipment_assignments_shipment_id", table_name="shipment_assignments")
    op.drop_table("shipment_assignments")
    op.drop_index("ix_delivery_agents_status", table_name="delivery_agents")
    op.drop_index("ix_delivery_agents_agent_type", table_name="delivery_agents")
    op.drop_index("ix_delivery_agents_user_id", table_name="delivery_agents")
    op.drop_table("delivery_agents")
