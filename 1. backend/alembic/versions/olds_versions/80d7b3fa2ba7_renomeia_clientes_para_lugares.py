"""Renomeia clientes para lugares

Revision ID: 80d7b3fa2ba7
Revises: b097c578d75d
Create Date: 2025-08-26 23:12:12.303551

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '80d7b3fa2ba7'
down_revision: Union[str, None] = 'b097c578d75d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Renomeia tabela clientes -> lugares
    op.rename_table('clientes', 'lugares')

    # Renomeia coluna cliente_id -> lugar_id em dispositivos
    op.alter_column(
        'dispositivos',
        'cliente_id',
        new_column_name='lugar_id'
    )

    # Ajusta a constraint de FK (drop antiga e cria nova)
    op.drop_constraint('dispositivos_cliente_id_fkey', 'dispositivos', type_='foreignkey')
    op.create_foreign_key(
        'dispositivos_lugar_id_fkey',
        'dispositivos',
        'lugares',
        ['lugar_id'],
        ['id']
    )


def downgrade() -> None:
    # Volta FK para clientes
    op.drop_constraint('dispositivos_lugar_id_fkey', 'dispositivos', type_='foreignkey')
    op.create_foreign_key(
        'dispositivos_cliente_id_fkey',
        'dispositivos',
        'clientes',
        ['cliente_id'],
        ['id']
    )

    # Volta nome da coluna
    op.alter_column(
        'dispositivos',
        'lugar_id',
        new_column_name='cliente_id'
    )

    # Volta tabela para clientes
    op.rename_table('lugares', 'clientes')

