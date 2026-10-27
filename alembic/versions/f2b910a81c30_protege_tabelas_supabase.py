"""Restringe o acesso direto pela Data API do Supabase.

Revision ID: f2b910a81c30
Revises: d91abb6fa934
"""
from alembic import op

revision = 'f2b910a81c30'
down_revision = 'd91abb6fa934'
branch_labels = None
depends_on = None

TABELAS = ('cargas', 'pedidos', 'usuarios', 'historico_status', 'alembic_version')


def upgrade():
    if op.get_bind().dialect.name == 'postgresql':
        for tabela in TABELAS:
            op.execute(f'ALTER TABLE "{tabela}" ENABLE ROW LEVEL SECURITY')
        # A API usa conexão de servidor pelo usuário postgres; navegadores não
        # recebem políticas de acesso direto às tabelas nem credenciais do banco.


def downgrade():
    if op.get_bind().dialect.name == 'postgresql':
        for tabela in TABELAS:
            op.execute(f'ALTER TABLE "{tabela}" DISABLE ROW LEVEL SECURITY')
