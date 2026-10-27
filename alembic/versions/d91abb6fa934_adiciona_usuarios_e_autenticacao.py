"""adiciona usuarios e autenticacao

Revision ID: d91abb6fa934
Revises: 11c007e7178c
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "d91abb6fa934"
down_revision: Union[str, Sequence[str], None] = "11c007e7178c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario", sa.String(length=50), nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("senha_hash", sa.String(length=255), nullable=False),
        sa.Column("perfil", sa.String(length=30), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("usuarios", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_usuarios_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_usuarios_usuario"), ["usuario"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("usuarios", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_usuarios_usuario"))
        batch_op.drop_index(batch_op.f("ix_usuarios_id"))
    op.drop_table("usuarios")
