"""Add persistent authentication session revocation and login rate-limit tables.

Revision ID: 0002_auth_security_hardening
Revises: 0001_initial_schema
Create Date: 2026-11-11
"""
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa

revision: str = "0002_auth_security_hardening"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set:
    if context.is_offline_mode():
        return set()
    bind = op.get_bind()
    return set(sa.inspect(bind).get_table_names())


def upgrade() -> None:
    existing = _existing_tables()

    if "revoked_sessions" not in existing:
        op.create_table(
            "revoked_sessions",
            sa.Column("jti", sa.String(length=128), primary_key=True, nullable=False),
            sa.Column("expires_at", sa.Float(), nullable=False),
            sa.Column("revoked_at", sa.Float(), nullable=False),
        )
        op.create_index("ix_revoked_sessions_expires_at", "revoked_sessions", ["expires_at"], unique=False)

    if "login_attempt_buckets" not in existing:
        op.create_table(
            "login_attempt_buckets",
            sa.Column("bucket_key", sa.String(length=128), primary_key=True, nullable=False),
            sa.Column("attempt_timestamps", sa.Text(), nullable=False),
            sa.Column("window_expires_at", sa.Float(), nullable=False),
            sa.Column("updated_at", sa.Float(), nullable=False),
        )
        op.create_index(
            "ix_login_attempt_buckets_window_expires_at",
            "login_attempt_buckets",
            ["window_expires_at"],
            unique=False,
        )
        op.create_index(
            "ix_login_attempt_buckets_updated_at",
            "login_attempt_buckets",
            ["updated_at"],
            unique=False,
        )


def downgrade() -> None:
    existing = _existing_tables()

    if "login_attempt_buckets" in existing:
        op.drop_index("ix_login_attempt_buckets_updated_at", table_name="login_attempt_buckets")
        op.drop_index("ix_login_attempt_buckets_window_expires_at", table_name="login_attempt_buckets")
        op.drop_table("login_attempt_buckets")

    if "revoked_sessions" in existing:
        op.drop_index("ix_revoked_sessions_expires_at", table_name="revoked_sessions")
        op.drop_table("revoked_sessions")

