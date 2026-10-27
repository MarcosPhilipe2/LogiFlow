"""adiciona historico de status

Revision ID: 11c007e7178c
Revises: a9fe80dcadbf
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "11c007e7178c"
down_revision: Union[str, Sequence[str], None] = "a9fe80dcadbf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "historico_status",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tipo_entidade", sa.String(length=20), nullable=False),
        sa.Column("entidade_id", sa.Integer(), nullable=False),
        sa.Column("identificador", sa.String(length=100), nullable=False),
        sa.Column("status_anterior", sa.String(length=30), nullable=True),
        sa.Column("status_novo", sa.String(length=30), nullable=False),
        sa.Column("origem", sa.String(length=30), nullable=False),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_historico_status_id", "historico_status", ["id"], unique=False)
    op.create_index("ix_historico_status_tipo_entidade", "historico_status", ["tipo_entidade"], unique=False)
    op.create_index("ix_historico_status_entidade_id", "historico_status", ["entidade_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_historico_status_entidade_id", table_name="historico_status")
    op.drop_index("ix_historico_status_tipo_entidade", table_name="historico_status")
    op.drop_index("ix_historico_status_id", table_name="historico_status")
    op.drop_table("historico_status")
