"""add task_lists order_index

Revision ID: 451a84a4c75b
Revises: 8b5b6158e663
Create Date: 2026-09-14 23:05:05.040408

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '451a84a4c75b'
down_revision: Union[str, Sequence[str], None] = '8b5b6158e663'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('task_lists', sa.Column('order_index', sa.Integer(), nullable=True))
    # Backfill existing rows with a stable 0-based order per tenant matching
    # prior creation order, same pattern as tasks.order_index.
    op.execute(
        """
        UPDATE task_lists t
        SET order_index = sub.rn
        FROM (
            SELECT id, ROW_NUMBER() OVER (
                PARTITION BY tenant_id ORDER BY created_at
            ) - 1 AS rn
            FROM task_lists
        ) sub
        WHERE t.id = sub.id
        """
    )
    op.alter_column('task_lists', 'order_index', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('task_lists', 'order_index')
