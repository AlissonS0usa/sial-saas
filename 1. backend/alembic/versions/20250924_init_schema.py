"""Init schema (squash)

Revision ID: 20250924_init_schema
Revises: 
Create Date: 2025-09-24 21:00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20250924_init_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # usuarios
    op.create_table(
        "usuarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("nome", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("senha_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="CLIENTE"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_usuarios_id", "usuarios", ["id"], unique=False)
    op.create_index("ix_usuarios_email", "usuarios", ["email"], unique=True)

    # lugares
    op.create_table(
        "lugares",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("nome", sa.String(), nullable=False),
        sa.Column("cep", sa.String(), nullable=False),
        sa.Column("rua", sa.String(), nullable=False),
        sa.Column("numero", sa.String(), nullable=False),
        sa.Column("bairro", sa.String(), nullable=False),
        sa.Column("cidade", sa.String(), nullable=False),
        sa.Column("estado", sa.String(), nullable=False),
        sa.Column("complemento", sa.String(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], name="lugares_usuario_id_fkey"),
    )
    op.create_index("ix_lugares_id", "lugares", ["id"], unique=False)

    # dispositivos
    op.create_table(
        "dispositivos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("nome", sa.String(), nullable=False),
        sa.Column("localizacao", sa.String(), nullable=True),
        sa.Column("lugar_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["lugar_id"], ["lugares.id"], name="dispositivos_lugar_id_fkey"),
    )
    op.create_index("ix_dispositivos_id", "dispositivos", ["id"], unique=False)
    op.create_index("ix_dispositivos_lugar_id", "dispositivos", ["lugar_id"], unique=False)

    # leituras
    op.create_table(
        "leituras",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("dispositivo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dados", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["dispositivo_id"], ["dispositivos.id"], name="leituras_dispositivo_id_fkey"),
    )
    op.create_index("ix_leituras_id", "leituras", ["id"], unique=False)
    op.create_index("ix_leituras_dispositivo_id", "leituras", ["dispositivo_id"], unique=False)
    op.create_index("ix_leituras_timestamp", "leituras", ["timestamp"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_leituras_timestamp", table_name="leituras")
    op.drop_index("ix_leituras_dispositivo_id", table_name="leituras")
    op.drop_index("ix_leituras_id", table_name="leituras")
    op.drop_table("leituras")

    op.drop_index("ix_dispositivos_lugar_id", table_name="dispositivos")
    op.drop_index("ix_dispositivos_id", table_name="dispositivos")
    op.drop_table("dispositivos")

    op.drop_index("ix_lugares_id", table_name="lugares")
    op.drop_table("lugares")

    op.drop_index("ix_usuarios_email", table_name="usuarios")
    op.drop_index("ix_usuarios_id", table_name="usuarios")
    op.drop_table("usuarios")
