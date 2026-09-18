"""add task_templates

Revision ID: d58a3f1c7b04
Revises: c41d7b8a92e5
Create Date: 2026-09-18 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd58a3f1c7b04'
down_revision: Union[str, Sequence[str], None] = 'c41d7b8a92e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'task_templates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('list_id', sa.UUID(), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column(
            'priority',
            postgresql.ENUM(name='task_priority', create_type=False),
            nullable=False,
            # The enum stores member names, not values — see the tasks table.
            server_default='MEDIUM',
        ),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('items', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['list_id'], ['task_lists.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_task_templates_tenant_id', 'task_templates', ['tenant_id'])
    op.create_index('ix_task_templates_list_id', 'task_templates', ['list_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_task_templates_list_id', table_name='task_templates')
    op.drop_index('ix_task_templates_tenant_id', table_name='task_templates')
    op.drop_table('task_templates')
