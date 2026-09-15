"""cascade delete subtasks on parent task deletion

Revision ID: 47c5e74fb593
Revises: 451a84a4c75b
Create Date: 2026-09-15 16:22:56.941781

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '47c5e74fb593'
down_revision: Union[str, Sequence[str], None] = '451a84a4c75b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint('fk_tasks_parent_task_id_tasks', 'tasks', type_='foreignkey')
    op.create_foreign_key(
        'fk_tasks_parent_task_id_tasks',
        'tasks', 'tasks', ['parent_task_id'], ['id'], ondelete='CASCADE',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_tasks_parent_task_id_tasks', 'tasks', type_='foreignkey')
    op.create_foreign_key(
        'fk_tasks_parent_task_id_tasks',
        'tasks', 'tasks', ['parent_task_id'], ['id'], ondelete='SET NULL',
    )
