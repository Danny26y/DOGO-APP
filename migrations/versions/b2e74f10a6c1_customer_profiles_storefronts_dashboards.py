"""customer profiles, address book, storefront profile and dashboard data

Revision ID: b2e74f10a6c1
Revises: beb9c511b6ca
Create Date: 2026-10-29 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b2e74f10a6c1"
down_revision = "beb9c511b6ca"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("full_name", sa.String(length=160), nullable=True))
    op.add_column("users", sa.Column("phone", sa.String(length=32), nullable=True))
    op.create_table(
        "customer_addresses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("label", sa.String(length=60), nullable=False),
        sa.Column("recipient_name", sa.String(length=160), nullable=False),
        sa.Column("recipient_phone", sa.String(length=32), nullable=False),
        sa.Column("address_line1", sa.String(length=250), nullable=False),
        sa.Column("address_line2", sa.String(length=250), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=False),
        sa.Column("state", sa.String(length=120), nullable=False),
        sa.Column("postal_code", sa.String(length=24), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("delivery_instructions", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customer_addresses_user_id", "customer_addresses", ["user_id"])
    op.create_index(
        "uq_customer_address_default_per_user",
        "customer_addresses",
        ["user_id"],
        unique=True,
        sqlite_where=sa.text("is_default = 1"),
        postgresql_where=sa.text("is_default IS TRUE"),
    )
    op.create_table(
        "merchant_store_profiles",
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("storefront_slug", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("support_email", sa.String(length=320), nullable=True),
        sa.Column("support_phone", sa.String(length=32), nullable=True),
        sa.Column("website_url", sa.String(length=500), nullable=True),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("organization_id"),
        sa.UniqueConstraint("storefront_slug"),
    )
    op.create_index("ix_merchant_store_profiles_storefront_slug", "merchant_store_profiles", ["storefront_slug"], unique=True)


def downgrade():
    op.drop_index("ix_merchant_store_profiles_storefront_slug", table_name="merchant_store_profiles")
    op.drop_table("merchant_store_profiles")
    op.drop_index("uq_customer_address_default_per_user", table_name="customer_addresses")
    op.drop_index("ix_customer_addresses_user_id", table_name="customer_addresses")
    op.drop_table("customer_addresses")
    op.drop_column("users", "phone")
    op.drop_column("users", "full_name")
