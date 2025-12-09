"""init schema

Revision ID: 8c4bdc8ea2ce
Revises: 20250924_init_schema
Create Date: 2025-09-24 22:39:26.538973

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c4bdc8ea2ce'
down_revision: Union[str, None] = '20250924_init_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
