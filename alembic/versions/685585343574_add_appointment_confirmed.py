"""add appointment confirmed

Revision ID: 685585343574
Revises: 3334ab99d032
Create Date: 2026-09-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '685585343574'
down_revision: Union[str, Sequence[str], None] = '3334ab99d032'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'appointments',
        sa.Column('confirmed', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column('appointments', 'confirmed', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('appointments', 'confirmed')
