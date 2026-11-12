"""email otp and customer identity review

Revision ID: 1b8d440ea732
Revises: 0a2f5c78d9e1
"""

import sqlalchemy as sa
from alembic import op

revision = "1b8d440ea732"
down_revision = "0a2f5c78d9e1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table(
        "email_otps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_email_otps_user_id", "email_otps", ["user_id"])
    op.create_table(
        "customer_identity_submissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_type", sa.String(32), nullable=False),
        sa.Column("storage_name", sa.String(100), nullable=False, unique=True),
        sa.Column("original_filename", sa.String(200), nullable=False),
        sa.Column("content_type", sa.String(80), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("review_note", sa.String(500)),
        sa.Column("reviewed_by_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_customer_identity_submissions_user_id", "customer_identity_submissions", ["user_id"])
    op.create_index("ix_customer_identity_submissions_status", "customer_identity_submissions", ["status"])


def downgrade():
    op.drop_index("ix_customer_identity_submissions_status", table_name="customer_identity_submissions")
    op.drop_index("ix_customer_identity_submissions_user_id", table_name="customer_identity_submissions")
    op.drop_table("customer_identity_submissions")
    op.drop_index("ix_email_otps_user_id", table_name="email_otps")
    op.drop_table("email_otps")
    op.drop_column("users", "email_verified")
