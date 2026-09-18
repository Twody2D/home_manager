"""add task_templates description

Revision ID: e6b92c4d1a37
Revises: d58a3f1c7b04
Create Date: 2026-09-18 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6b92c4d1a37'
down_revision: Union[str, Sequence[str], None] = 'd58a3f1c7b04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Per-item descriptions live inside the existing items JSON, so only the
    # template's own (root task) description needs a column.
    op.add_column('task_templates', sa.Column('description', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('task_templates', 'description')
