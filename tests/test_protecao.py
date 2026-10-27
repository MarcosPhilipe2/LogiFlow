import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import app as app_logiflow
from app.protecao import LimitadorPorCliente, ProtecaoContraSobrecarga

LIMITES_FOLGADOS = {
    "max_simultaneas": 100,
    "por_minuto": 6000,
    "rajada": 1000,
    "login_por_minuto": 6000,
    "login_rajada": 1000,
    "max_logins_simultaneos": 100,
    "max_escritas_na_fila": 100,
}


class RelogioFalso:
    def __init__(self):
        self.agora = 1000.0

    def __call__(self):
        return self.agora


def app_simples(**limites):
    interno = FastAPI()

    @interno.get("/ping")
    def ping():
        return {"ok": True}

    @interno.post("/auth/login")
    def login():
        return {"ok": True}

    return ProtecaoContraSobrecarga(interno, **(LIMITES_FOLGADOS | limites))


def test_token_bucket_libera_rajada_e_repoe_com_o_tempo():
    relogio = RelogioFalso()
    limitador = LimitadorPorCliente(por_minuto=60, rajada=3, relogio=relogio)

    assert [limitador.consumir("10.0.0.1") for _ in range(3)] == [0, 0, 0]
    assert limitador.consumir("10.0.0.1") == 1.0  # 60/min = 1 ficha por segundo
    assert limitador.consumir("10.0.0.2") == 0  # outro IP tem o próprio balde

    relogio.agora += 1
    assert limitador.consumir("10.0.0.1") == 0
    assert limitador.consumir("10.0.0.1") > 0


def test_baldes_parados_sao_descartados():
    relogio = RelogioFalso()
    limitador = LimitadorPorCliente(por_minuto=60, rajada=3, relogio=relogio)
    limitador.consumir("10.0.0.1")
    relogio.agora += LimitadorPorCliente.INTERVALO_LIMPEZA + 1
    limitador.consumir("10.0.0.2")
    assert list(limitador.baldes) == ["10.0.0.2"]


def test_excesso_por_ip_recebe_429_com_retry_after():
    cliente = TestClient(app_simples(por_minuto=60, rajada=3))
    assert [cliente.get("/ping").status_code for _ in range(3)] == [200, 200, 200]

    resposta = cliente.get("/ping")
    assert resposta.status_code == 429
    assert int(resposta.headers["retry-after"]) >= 1
    assert "Muitas requisições" in resposta.json()["detail"]


def test_login_tem_limite_proprio():
    cliente = TestClient(app_simples(login_por_minuto=10, login_rajada=2))
    assert [cliente.post("/auth/login").status_code for _ in range(3)] == [200, 200, 429]
    assert cliente.get("/ping").status_code == 200  # as demais rotas continuam liberadas


def protecao_com_app_lento(**limites):
    """Protege um app que só responde quando o evento retornado é liberado.

    `protecao.atendidas` registra, em ordem, os IPs cujas requisições chegaram ao app.
    """
    liberar = asyncio.Event()

    async def app_lento(scope, receive, send):
        protecao.atendidas.append(scope["client"][0])
        await liberar.wait()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    protecao = ProtecaoContraSobrecarga(app_lento, **(LIMITES_FOLGADOS | limites))
    protecao.atendidas = []

    async def chamar(caminho: str, ip: str, metodo: str = "GET") -> int:
        enviados = []

        async def receive():
            return {"type": "http.request", "body": b""}

        async def send(mensagem):
            enviados.append(mensagem)

        escopo = {"type": "http", "method": metodo, "path": caminho, "client": (ip, 1234)}
        await protecao(escopo, receive, send)
        return enviados[0]["status"]

    return protecao, liberar, chamar


def test_teto_global_recusa_com_503_sem_enfileirar():
    async def cenario():
        protecao, liberar, chamar = protecao_com_app_lento(max_simultaneas=2)
        tarefas = [asyncio.create_task(chamar("/x", f"10.0.0.{i}")) for i in range(3)]
        await asyncio.sleep(0.01)
        assert tarefas[2].done() and tarefas[2].result() == 503
        assert protecao.em_andamento == 2

        liberar.set()
        assert [await tarefa for tarefa in tarefas[:2]] == [200, 200]
        assert protecao.em_andamento == 0

    asyncio.run(cenario())


def test_teto_de_logins_nao_bloqueia_as_outras_rotas():
    async def cenario():
        protecao, liberar, chamar = protecao_com_app_lento(max_logins_simultaneos=1)
        primeiro_login = asyncio.create_task(chamar("/auth/login", "10.0.0.1", "POST"))
        segundo_login = asyncio.create_task(chamar("/auth/login", "10.0.0.2", "POST"))
        leitura = asyncio.create_task(chamar("/pedidos", "10.0.0.3"))
        await asyncio.sleep(0.01)
        assert segundo_login.done() and segundo_login.result() == 503
        assert not leitura.done()  # a leitura entrou normalmente e está sendo atendida

        liberar.set()
        assert [await primeiro_login, await leitura] == [200, 200]
        assert (protecao.em_andamento, protecao.logins_em_andamento) == (0, 0)

    asyncio.run(cenario())


def test_gravacoes_sao_atendidas_uma_de_cada_vez_em_ordem():
    async def cenario():
        protecao, liberar, chamar = protecao_com_app_lento()
        gravacoes = [asyncio.create_task(chamar("/pedidos", f"10.0.0.{i}", "POST")) for i in range(3)]
        leitura = asyncio.create_task(chamar("/pedidos", "10.0.0.9"))
        await asyncio.sleep(0.01)
        # Só a primeira gravação chegou ao app; a leitura não entra na fila de gravação.
        assert protecao.atendidas == ["10.0.0.0", "10.0.0.9"]

        liberar.set()
        assert [await tarefa for tarefa in gravacoes] == [200, 200, 200]
        assert protecao.atendidas == ["10.0.0.0", "10.0.0.9", "10.0.0.1", "10.0.0.2"]
        assert await leitura == 200
        assert protecao.escritas_na_fila == 0

    asyncio.run(cenario())


def test_fila_de_gravacao_cheia_responde_503():
    async def cenario():
        protecao, liberar, chamar = protecao_com_app_lento(max_escritas_na_fila=2)
        gravacoes = [asyncio.create_task(chamar("/pedidos", f"10.0.0.{i}", "PUT")) for i in range(3)]
        await asyncio.sleep(0.01)
        assert gravacoes[2].done() and gravacoes[2].result() == 503

        liberar.set()
        assert [await tarefa for tarefa in gravacoes[:2]] == [200, 200]

    asyncio.run(cenario())


def test_limite_de_login_vale_para_a_rota_real(client):
    limites = LIMITES_FOLGADOS | {"login_por_minuto": 10, "login_rajada": 2}
    protegido = TestClient(ProtecaoContraSobrecarga(app_logiflow, **limites))
    dados = {"username": "admin", "password": "senha-errada"}
    codigos = [protegido.post("/auth/login", data=dados).status_code for _ in range(3)]
    assert codigos == [401, 401, 429]


def test_api_registra_a_protecao():
    assert any(m.cls is ProtecaoContraSobrecarga for m in app_logiflow.user_middleware)
