"""ajuste final

Revision ID: b477c807e638
Revises: 8c4bdc8ea2ce
Create Date: 2025-09-24 22:44:48.525748

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b477c807e638'
down_revision: Union[str, None] = '8c4bdc8ea2ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
