"""add notification structured fields

Revision ID: a4a3170535c3
Revises: 823a33eb0290
Create Date: 2026-09-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4a3170535c3'
down_revision: Union[str, Sequence[str], None] = '823a33eb0290'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('notifications', sa.Column('customer_name', sa.String(length=255), nullable=True))
    op.add_column('notifications', sa.Column('service_name', sa.String(length=255), nullable=True))
    op.add_column('notifications', sa.Column('appointment_time', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('notifications', 'appointment_time')
    op.drop_column('notifications', 'service_name')
    op.drop_column('notifications', 'customer_name')
