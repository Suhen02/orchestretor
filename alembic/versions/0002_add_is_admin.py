"""add is_admin to users

Revision ID: 0002_add_is_admin
Revises: 0001_initial_schema
Create Date: 2026-06-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0002_add_is_admin"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # FIX: is_admin was missing from the users table; required for admin
    #      dashboard login guard, /admin/jobs endpoint, and
    #      bootstrap.ensure_admin_user().
    op.add_column(
        "users",
        sa.Column(
            "is_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_admin")