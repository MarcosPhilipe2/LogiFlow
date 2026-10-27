"""adiciona observacao ao pedido

Revision ID: 1eb630ce322c
Revises: 11c36d4e8f5d
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "1eb630ce322c"
down_revision: Union[str, Sequence[str], None] = "11c36d4e8f5d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("pedidos", schema=None) as batch_op:
        batch_op.add_column(sa.Column("observacao", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("pedidos", schema=None) as batch_op:
        batch_op.drop_column("observacao")
