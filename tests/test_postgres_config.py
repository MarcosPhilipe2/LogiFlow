import pytest
from sqlalchemy.engine import make_url
from app.conexao import normalizar_url_banco


@pytest.mark.parametrize('prefixo', ['postgres://', 'postgresql://', 'postgresql+psycopg://'])
def test_normaliza_driver_postgres_e_ssl(prefixo):
    resultado = make_url(normalizar_url_banco(prefixo + 'postgres.ref:senha%40segura@pooler.example:5432/postgres'))
    assert resultado.drivername == 'postgresql+psycopg'
    assert resultado.password == 'senha@segura'
    assert resultado.query['sslmode'] == 'require'


def test_preserva_ssl_e_opcoes():
    url = make_url(normalizar_url_banco('postgresql://user:senha@host/db?sslmode=verify-full&application_name=logiflow'))
    assert url.query['sslmode'] == 'verify-full'
    assert url.query['application_name'] == 'logiflow'


def test_preserva_sqlite():
    assert normalizar_url_banco('sqlite:///./logiflow.db') == 'sqlite:///./logiflow.db'


def test_url_com_percentual_compativel_com_alembic():
    from alembic.config import Config
    url = normalizar_url_banco('postgresql://user:senha%25e%40@host/db')
    config = Config()
    config.set_main_option('sqlalchemy.url', url.replace('%', '%%'))
    assert make_url(config.get_main_option('sqlalchemy.url')).password == 'senha%e@'
