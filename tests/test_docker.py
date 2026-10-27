import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.backup_docker import fazer_backup
from scripts.configurar_docker import criar_configuracao

RAIZ = Path(__file__).resolve().parent.parent


def test_configuracao_preserva_senha_literal_e_gera_segredos_distintos():
    senha = 'Uma$senha#com"aspas'
    a = criar_configuracao(' ADMIN ', ' Marcos ', senha, senha)
    b = criar_configuracao('admin', 'Marcos', senha, senha)
    assert f'LOGIFLOW_ADMIN_SENHA={senha}\n' in a
    assert 'LOGIFLOW_ADMIN_USUARIO=admin\n' in a
    assert a.splitlines()[0] != b.splitlines()[0]
    assert len(a.splitlines()[0].split('=')[1]) == 64


@pytest.mark.parametrize('senha,confirmacao', [('curta', 'curta'), ('SenhaValida', 'outra'), ('Senha\ninvalida', 'Senha\ninvalida')])
def test_configuracao_rejeita_senha_invalida(senha, confirmacao):
    with pytest.raises(ValueError):
        criar_configuracao('admin', 'Marcos', senha, confirmacao)


def test_backup_inclui_gravacoes_em_wal(tmp_path):
    origem, destino = tmp_path / 'origem.db', tmp_path / 'backup.db'
    with sqlite3.connect(origem) as banco:
        banco.execute('PRAGMA journal_mode=WAL')
        banco.execute('CREATE TABLE exemplo (nome TEXT)')
        banco.execute("INSERT INTO exemplo VALUES ('pedido novo')")
        banco.commit()
        fazer_backup(origem, destino)
    with sqlite3.connect(destino) as banco:
        assert banco.execute('SELECT nome FROM exemplo').fetchone()[0] == 'pedido novo'
    with pytest.raises(FileExistsError):
        fazer_backup(origem, destino)
    with pytest.raises(FileNotFoundError):
        fazer_backup(tmp_path / 'nao-existe.db', tmp_path / 'outra.db')


def test_inicializacao_sem_terminal_e_idempotente(tmp_path):
    env = os.environ | {
        'DATABASE_URL': 'sqlite:///' + str(tmp_path / 'container.db'),
        'JWT_SECRET_KEY': 'segredo-para-testar-container-com-32-caracteres',
        'LOGIFLOW_ADMIN_USUARIO': 'admin-docker',
        'LOGIFLOW_ADMIN_NOME': 'Administrador Docker',
        'LOGIFLOW_ADMIN_SENHA': 'SenhaDocker123',
    }
    codigo = 'from docker.iniciar import preparar; preparar()'
    for _ in range(2):
        resultado = subprocess.run([sys.executable, '-c', codigo], cwd=RAIZ, env=env, capture_output=True, text=True, timeout=30)
        assert resultado.returncode == 0, resultado.stderr + resultado.stdout
    with sqlite3.connect(tmp_path / 'container.db') as banco:
        assert banco.execute('SELECT count(*) FROM usuarios').fetchone()[0] == 1
        assert banco.execute('SELECT count(*) FROM pedidos').fetchone()[0] == 0


def test_primeiro_admin_exige_credenciais_sem_input(tmp_path):
    env = os.environ | {
        'DATABASE_URL': 'sqlite:///' + str(tmp_path / 'vazio.db'),
        'JWT_SECRET_KEY': 'segredo-para-testar-container-com-32-caracteres',
    }
    env.pop('LOGIFLOW_ADMIN_USUARIO', None)
    env.pop('LOGIFLOW_ADMIN_SENHA', None)
    resultado = subprocess.run([sys.executable, '-c', 'from docker.iniciar import preparar; preparar()'], cwd=RAIZ, env=env, capture_output=True, text=True, timeout=30)
    assert resultado.returncode != 0
    assert 'Primeira instalação' in resultado.stderr
