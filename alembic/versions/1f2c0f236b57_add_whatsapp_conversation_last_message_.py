"""add whatsapp conversation last_message_id

Revision ID: 1f2c0f236b57
Revises: a4a3170535c3
Create Date: 2026-09-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f2c0f236b57'
down_revision: Union[str, Sequence[str], None] = 'a4a3170535c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('whatsapp_conversations', sa.Column('last_message_id', sa.String(length=100), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('whatsapp_conversations', 'last_message_id')
