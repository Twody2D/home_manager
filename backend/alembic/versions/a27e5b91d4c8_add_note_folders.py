"""add note_folders

Revision ID: a27e5b91d4c8
Revises: f1a7d3e9c520
Create Date: 2026-09-21 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a27e5b91d4c8'
down_revision: Union[str, Sequence[str], None] = 'f1a7d3e9c520'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'note_folders',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_note_folders_tenant_id', 'note_folders', ['tenant_id'])

    op.add_column('notes', sa.Column('folder_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_notes_folder_id_note_folders',
        'notes',
        'note_folders',
        ['folder_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_notes_folder_id', 'notes', ['folder_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_notes_folder_id', table_name='notes')
    op.drop_constraint('fk_notes_folder_id_note_folders', 'notes', type_='foreignkey')
    op.drop_column('notes', 'folder_id')
    op.drop_index('ix_note_folders_tenant_id', table_name='note_folders')
    op.drop_table('note_folders')
