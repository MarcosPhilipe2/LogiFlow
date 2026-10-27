"""estrutura inicial do logiflow

Revision ID: 11c36d4e8f5d
Revises:
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "11c36d4e8f5d"
down_revision: Union[str, Sequence[str], None] = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cargas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("numero_carga", sa.String(length=50), nullable=False),
        sa.Column("transportadora", sa.String(length=150), nullable=False),
        sa.Column("veiculo", sa.String(length=50), nullable=True),
        sa.Column("motorista", sa.String(length=150), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("peso_total", sa.Float(), nullable=False),
        sa.Column("data_saida", sa.DateTime(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cargas_id", "cargas", ["id"], unique=False)
    op.create_index("ix_cargas_numero_carga", "cargas", ["numero_carga"], unique=True)

    op.create_table(
        "pedidos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("numero_pedido", sa.String(length=50), nullable=False),
        sa.Column("cliente", sa.String(length=150), nullable=False),
        sa.Column("cidade", sa.String(length=100), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("peso", sa.Float(), nullable=False),
        sa.Column("valor_total", sa.Float(), nullable=False),
        sa.Column("carga_id", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["carga_id"], ["cargas.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pedidos_id", "pedidos", ["id"], unique=False)
    op.create_index("ix_pedidos_numero_pedido", "pedidos", ["numero_pedido"], unique=True)
    op.create_index("ix_pedidos_carga_id", "pedidos", ["carga_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_pedidos_carga_id", table_name="pedidos")
    op.drop_index("ix_pedidos_numero_pedido", table_name="pedidos")
    op.drop_index("ix_pedidos_id", table_name="pedidos")
    op.drop_table("pedidos")
    op.drop_index("ix_cargas_numero_carga", table_name="cargas")
    op.drop_index("ix_cargas_id", table_name="cargas")
    op.drop_table("cargas")
