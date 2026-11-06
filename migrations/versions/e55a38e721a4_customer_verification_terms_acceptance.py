"""record versioned customer verification terms acceptance

Revision ID: e55a38e721a4
Revises: d0a834e2c951
Create Date: 2026-11-06 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "e55a38e721a4"
down_revision = "d0a834e2c951"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "customer_verification_consents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("terms_version", sa.String(length=64), nullable=False),
        sa.Column("privacy_policy_version", sa.String(length=64), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "terms_version", "privacy_policy_version", name="uq_customer_consent_user_versions"),
    )
    op.create_index("ix_customer_verification_consents_user_id", "customer_verification_consents", ["user_id"])


def downgrade():
    op.drop_index("ix_customer_verification_consents_user_id", table_name="customer_verification_consents")
    op.drop_table("customer_verification_consents")
