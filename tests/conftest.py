import os
from itertools import count

os.environ.setdefault("JWT_SECRET_KEY", "chave-usada-somente-nos-testes-automatizados")
# O rate limit fica ativo nos testes, mas folgado: os testes fazem muitas requisições seguidas.
# O comportamento dos limites é testado em test_protecao.py, com valores baixos.
for _variavel in ("LIMITE_POR_MINUTO", "LIMITE_RAJADA", "LIMITE_LOGIN_POR_MINUTO", "LIMITE_LOGIN_RAJADA"):
    os.environ.setdefault(_variavel, "1000000")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.enums.perfil_usuario import PerfilUsuario
from app.main import app
from app.models.usuario import Usuario
from app.services.auth import gerar_hash_senha

SENHA = "senha-de-teste"
SENHA_HASH = gerar_hash_senha(SENHA)
LOGINS = {
    PerfilUsuario.ADMINISTRADOR: "admin",
    PerfilUsuario.OPERACAO: "operador",
    PerfilUsuario.CONSULTA: "consulta",
}


@pytest.fixture
def fabrica_sessao():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False)
    engine.dispose()


@pytest.fixture
def client(fabrica_sessao):
    def get_db_teste():
        db = fabrica_sessao()
        try:
            yield db
        finally:
            db.close()

    with fabrica_sessao() as db:
        for perfil, login in LOGINS.items():
            db.add(Usuario(
                usuario=login,
                nome=f"Usuário {perfil.value}",
                senha_hash=SENHA_HASH,
                perfil=perfil.value,
                ativo=True,
            ))
        db.commit()

    app.dependency_overrides[get_db] = get_db_teste
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()


@pytest.fixture
def login(client):
    def fazer_login(usuario: str, senha: str = SENHA):
        return client.post("/auth/login", data={"username": usuario, "password": senha})

    return fazer_login


@pytest.fixture
def headers(login):
    tokens = {}

    def obter(perfil: PerfilUsuario):
        if perfil not in tokens:
            resposta = login(LOGINS[perfil])
            assert resposta.status_code == 200, resposta.text
            tokens[perfil] = {"Authorization": f"Bearer {resposta.json()['access_token']}"}
        return tokens[perfil]

    return obter


@pytest.fixture
def admin(headers):
    return headers(PerfilUsuario.ADMINISTRADOR)


@pytest.fixture
def operador(headers):
    return headers(PerfilUsuario.OPERACAO)


@pytest.fixture
def consulta(headers):
    return headers(PerfilUsuario.CONSULTA)


@pytest.fixture
def novo_pedido(client, admin):
    sequencia = count(1)

    def criar(**dados):
        corpo = {
            "numero_pedido": f"PED-{next(sequencia):04d}",
            "cliente": "Cliente Teste",
            "cidade": "Campinas",
            "uf": "SP",
            "peso": 10,
            "valor_total": 100,
        } | dados
        resposta = client.post("/pedidos", json=corpo, headers=admin)
        assert resposta.status_code == 201, resposta.text
        return resposta.json()

    return criar


@pytest.fixture
def nova_carga(client, admin):
    sequencia = count(1)

    def criar(**dados):
        corpo = {
            "numero_carga": f"CAR-{next(sequencia):04d}",
            "transportadora": "Transportadora Teste",
        } | dados
        resposta = client.post("/cargas", json=corpo, headers=admin)
        assert resposta.status_code == 201, resposta.text
        return resposta.json()

    return criar


@pytest.fixture
def vincular(client, admin):
    def executar(carga_id: int, pedido_id: int):
        resposta = client.post(f"/cargas/{carga_id}/pedidos/{pedido_id}", headers=admin)
        assert resposta.status_code == 200, resposta.text
        return resposta.json()

    return executar


@pytest.fixture
def avancar_carga(client, admin):
    def executar(carga_id: int, *lista_status: str):
        for novo_status in lista_status:
            resposta = client.put(f"/cargas/{carga_id}", json={"status": novo_status}, headers=admin)
            assert resposta.status_code == 200, resposta.text
        return resposta.json()

    return executar


@pytest.fixture
def mudar_status_pedido(client, admin):
    def executar(pedido_id: int, *lista_status: str):
        for novo_status in lista_status:
            resposta = client.put(f"/pedidos/{pedido_id}", json={"status": novo_status}, headers=admin)
            assert resposta.status_code == 200, resposta.text
        return resposta.json()

    return executar
