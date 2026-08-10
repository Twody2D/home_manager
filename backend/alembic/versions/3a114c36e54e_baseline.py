"""baseline

Revision ID: 3a114c36e54e
Revises: 
Create Date: 2026-08-10 12:42:40.849051

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = '3a114c36e54e'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
