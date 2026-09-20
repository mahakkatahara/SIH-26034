"""add_package_type_and_citation_verified_to_rules

Revision ID: dee740111ad5
Revises: 
Create Date: 2026-09-19 11:28:56.551608

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dee740111ad5'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'rules',
        sa.Column('package_type', sa.String(length=20), nullable=False, server_default='retail')
    )
    op.add_column(
        'rules',
        sa.Column('citation_verified', sa.Boolean(), nullable=False, server_default=sa.text('false'))
    )


def downgrade() -> None:
    op.drop_column('rules', 'citation_verified')
    op.drop_column('rules', 'package_type')
