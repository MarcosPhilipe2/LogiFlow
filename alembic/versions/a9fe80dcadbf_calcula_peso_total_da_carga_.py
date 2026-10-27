"""calcula peso total da carga automaticamente

Revision ID: a9fe80dcadbf
Revises: 1eb630ce322c
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "a9fe80dcadbf"
down_revision: Union[str, Sequence[str], None] = "1eb630ce322c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("cargas", schema=None) as batch_op:
        batch_op.drop_column("peso_total")


def downgrade() -> None:
    with op.batch_alter_table("cargas", schema=None) as batch_op:
        batch_op.add_column(sa.Column("peso_total", sa.Float(), nullable=False, server_default=sa.text("0")))
