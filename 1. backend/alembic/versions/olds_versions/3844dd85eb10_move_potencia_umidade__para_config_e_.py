"""Move potencia/umidade_* para config e remove colunas

Revision ID: 3844dd85eb10
Revises: 91ad746be777
Create Date: 2025-09-22 23:08:20.647057

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3844dd85eb10'
down_revision: Union[str, None] = '91ad746be777'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1) Garante que a coluna config exista (se já existe, ok)
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = [c["name"] for c in insp.get_columns("dispositivos")]
    if "config" not in cols:
        op.add_column("dispositivos", sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # 2) Copia dados antigos para config
    op.execute("""
    UPDATE dispositivos
    SET config = COALESCE(config, '{}'::jsonb)
          || COALESCE( (CASE WHEN umidade_min IS NOT NULL THEN jsonb_build_object('umidade_min', umidade_min) ELSE '{}'::jsonb END), '{}'::jsonb)
          || COALESCE( (CASE WHEN umidade_max IS NOT NULL THEN jsonb_build_object('umidade_max', umidade_max) ELSE '{}'::jsonb END), '{}'::jsonb)
          || COALESCE( (CASE WHEN potencia     IS NOT NULL THEN jsonb_build_object('potencia',     potencia)     ELSE '{}'::jsonb END), '{}'::jsonb)
    """)

    # 3) Drop das colunas antigas
    if "potencia" in cols:
        op.drop_column("dispositivos", "potencia")
    if "umidade_min" in cols:
        op.drop_column("dispositivos", "umidade_min")
    if "umidade_max" in cols:
        op.drop_column("dispositivos", "umidade_max")

def downgrade():
    # 1) Recria as colunas
    op.add_column("dispositivos", sa.Column("umidade_max", sa.Float(), nullable=True))
    op.add_column("dispositivos", sa.Column("umidade_min", sa.Float(), nullable=True))
    op.add_column("dispositivos", sa.Column("potencia", sa.Integer(), nullable=True))

    # 2) Restaura valores a partir de config
    op.execute("""
    UPDATE dispositivos
    SET umidade_min = NULLIF( (config->>'umidade_min'), '')::numeric,
        umidade_max = NULLIF( (config->>'umidade_max'), '')::numeric,
        potencia    = NULLIF( (config->>'potencia'), '')::int
    """)