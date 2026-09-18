"""add task_lists owner_user_id

Revision ID: c41d7b8a92e5
Revises: 47c5e74fb593
Create Date: 2026-09-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c41d7b8a92e5'
down_revision: Union[str, Sequence[str], None] = '47c5e74fb593'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('task_lists', sa.Column('owner_user_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_task_lists_owner_user_id_users',
        'task_lists',
        'users',
        ['owner_user_id'],
        ['id'],
        ondelete='SET NULL',
    )
    # Existing folders were created by whoever wanted them, so filing each
    # one under its creator matches how they were already being used; a
    # member can move any of them to the shared section afterwards.
    op.execute('UPDATE task_lists SET owner_user_id = created_by')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_task_lists_owner_user_id_users', 'task_lists', type_='foreignkey')
    op.drop_column('task_lists', 'owner_user_id')
