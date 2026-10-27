import pytest

PEDIDO = {"numero_pedido": "PED-X", "cliente": "Cliente", "cidade": "Campinas", "uf": "SP", "peso": 1, "valor_total": 1}


def resumo_historico(historico):
    return [(h["status_anterior"], h["status_novo"], h["origem"]) for h in historico]


def test_criar_pedido_normaliza_campos(client, admin):
    corpo = {
        "numero_pedido": "  ped-10 ",
        "cliente": "  ACME Ltda  ",
        "cidade": " Campinas ",
        "uf": "sp",
        "peso": 12.5,
        "valor_total": 99.9,
        "observacao": "Frágil",
    }
    resposta = client.post("/pedidos", json=corpo, headers=admin)
    assert resposta.status_code == 201
    pedido = resposta.json()
    assert pedido["numero_pedido"] == "PED-10"
    assert pedido["cliente"] == "ACME Ltda"
    assert pedido["cidade"] == "Campinas"
    assert pedido["uf"] == "SP"
    assert pedido["status"] == "Pendente"
    assert pedido["carga_id"] is None


def test_numero_de_pedido_duplicado(client, admin, novo_pedido):
    novo_pedido(numero_pedido="PED-1")
    resposta = client.post("/pedidos", json=PEDIDO | {"numero_pedido": " ped-1 "}, headers=admin)
    assert resposta.status_code == 409


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("numero_pedido", "   "),
        ("cliente", "    "),
        ("cidade", "  "),
        ("uf", "S "),
        ("uf", "12"),
        ("peso", -1),
    ],
)
def test_criar_pedido_rejeita_valores_invalidos(client, admin, campo, valor):
    resposta = client.post("/pedidos", json=PEDIDO | {campo: valor}, headers=admin)
    assert resposta.status_code == 422


def test_pedido_sempre_nasce_pendente(client, admin):
    assert client.post("/pedidos", json=PEDIDO | {"status": "Entregue"}, headers=admin).status_code == 422
    resposta = client.post("/pedidos", json=PEDIDO | {"status": "Pendente"}, headers=admin)
    assert resposta.status_code == 201
    assert resposta.json()["status"] == "Pendente"


def test_busca_por_numero_ignora_caixa_e_espacos(client, admin, novo_pedido):
    pedido = novo_pedido(numero_pedido="PED-77")
    assert client.get("/pedidos/numero/ped-77", headers=admin).json()["id"] == pedido["id"]

    resposta = client.put("/pedidos/numero/ped-77", json={"cliente": "Novo Cliente"}, headers=admin)
    assert resposta.status_code == 200
    assert resposta.json()["cliente"] == "Novo Cliente"


def test_pedido_inexistente(client, admin):
    assert client.get("/pedidos/999", headers=admin).status_code == 404
    assert client.get("/pedidos/numero/NADA", headers=admin).status_code == 404
    assert client.put("/pedidos/999", json={"cliente": "Fulano"}, headers=admin).status_code == 404
    assert client.get("/pedidos/999/historico", headers=admin).status_code == 404
    assert client.get("/pedidos/numero/NADA/historico", headers=admin).status_code == 404
    assert client.delete("/pedidos/999", headers=admin).status_code == 404


def test_listar_pedidos_mais_recentes_primeiro(client, admin, novo_pedido):
    primeiro = novo_pedido()
    segundo = novo_pedido()
    ids = [pedido["id"] for pedido in client.get("/pedidos", headers=admin).json()]
    assert ids == [segundo["id"], primeiro["id"]]


def test_atualizar_normaliza_como_na_criacao(client, admin, novo_pedido):
    pedido = novo_pedido()
    corpo = {"numero_pedido": " ped-xyz ", "cliente": "  Novo Cliente  ", "cidade": " Niterói ", "uf": "rj"}
    resposta = client.put(f"/pedidos/{pedido['id']}", json=corpo, headers=admin)
    assert resposta.status_code == 200
    atualizado = resposta.json()
    assert atualizado["numero_pedido"] == "PED-XYZ"
    assert atualizado["cliente"] == "Novo Cliente"
    assert atualizado["cidade"] == "Niterói"
    assert atualizado["uf"] == "RJ"


@pytest.mark.parametrize("campo", ["numero_pedido", "cliente", "cidade", "uf", "status", "peso", "valor_total"])
def test_atualizar_rejeita_nulo_em_campo_obrigatorio(client, admin, novo_pedido, campo):
    pedido = novo_pedido()
    resposta = client.put(f"/pedidos/{pedido['id']}", json={campo: None}, headers=admin)
    assert resposta.status_code == 422


def test_atualizar_permite_limpar_observacao(client, admin, novo_pedido):
    pedido = novo_pedido(observacao="Frágil")
    resposta = client.put(f"/pedidos/{pedido['id']}", json={"observacao": None}, headers=admin)
    assert resposta.status_code == 200
    assert resposta.json()["observacao"] is None


def test_atualizar_para_numero_existente(client, admin, novo_pedido):
    novo_pedido(numero_pedido="PED-A")
    outro = novo_pedido(numero_pedido="PED-B")
    resposta = client.put(f"/pedidos/{outro['id']}", json={"numero_pedido": "ped-a"}, headers=admin)
    assert resposta.status_code == 409
    assert "Já existe um pedido" in resposta.json()["detail"]


def test_transicoes_manuais_e_historico(client, admin, novo_pedido, mudar_status_pedido):
    pedido = novo_pedido()
    url = f"/pedidos/{pedido['id']}"

    assert client.put(url, json={"status": "Entregue"}, headers=admin).status_code == 409
    mudar_status_pedido(pedido["id"], "Em separação", "Pendente", "Cancelado")

    resposta = client.put(url, json={"status": "Pendente"}, headers=admin)
    assert resposta.status_code == 409
    assert "nenhuma" in resposta.json()["detail"]

    historico = client.get(f"{url}/historico", headers=admin).json()
    assert resumo_historico(historico) == [
        (None, "Pendente", "criacao"),
        ("Pendente", "Em separação", "manual"),
        ("Em separação", "Pendente", "manual"),
        ("Pendente", "Cancelado", "manual"),
    ]
    assert client.get(f"/pedidos/numero/{pedido['numero_pedido']}/historico", headers=admin).json() == historico


def test_status_de_transporte_so_mudam_pela_carga(client, admin, novo_pedido, mudar_status_pedido):
    pedido = novo_pedido()
    mudar_status_pedido(pedido["id"], "Em separação")
    resposta = client.put(f"/pedidos/{pedido['id']}", json={"status": "Carregado"}, headers=admin)
    assert resposta.status_code == 409
    assert "definido automaticamente pela carga" in resposta.json()["detail"]


def test_pedido_em_carga_so_pode_ser_cancelado_manualmente(client, admin, novo_pedido, nova_carga, vincular):
    carga = nova_carga()
    pedido = novo_pedido(peso=7)
    outro = novo_pedido(peso=3)
    vincular(carga["id"], pedido["id"])
    vincular(carga["id"], outro["id"])

    resposta = client.put(f"/pedidos/{pedido['id']}", json={"status": "Em separação"}, headers=admin)
    assert resposta.status_code == 409
    assert "só podem ser cancelados" in resposta.json()["detail"]

    resposta = client.put(f"/pedidos/{pedido['id']}", json={"status": "Cancelado"}, headers=admin)
    assert resposta.status_code == 200
    assert resposta.json()["carga_id"] is None
    assert client.get(f"/cargas/{carga['id']}", headers=admin).json()["peso_total"] == 3


def test_nao_exclui_pedido_vinculado_a_carga(client, admin, novo_pedido, nova_carga, vincular):
    carga = nova_carga()
    pedido = novo_pedido()
    vincular(carga["id"], pedido["id"])

    resposta = client.delete(f"/pedidos/{pedido['id']}", headers=admin)
    assert resposta.status_code == 409
    assert "Desvincule" in resposta.json()["detail"]

    client.delete(f"/cargas/{carga['id']}/pedidos/{pedido['id']}", headers=admin)
    assert client.delete(f"/pedidos/{pedido['id']}", headers=admin).status_code == 200


def test_listagem_com_filtros_e_paginacao(client, admin, novo_pedido, nova_carga, vincular, mudar_status_pedido):
    pedidos = [novo_pedido() for _ in range(5)]
    mudar_status_pedido(pedidos[0]["id"], "Cancelado")
    vincular(nova_carga()["id"], pedidos[1]["id"])

    resposta = client.get("/pedidos?limite=2", headers=admin)
    assert resposta.headers["X-Total-Count"] == "5"
    assert [p["id"] for p in resposta.json()] == [pedidos[4]["id"], pedidos[3]["id"]]
    assert [p["id"] for p in client.get("/pedidos?limite=2&offset=4", headers=admin).json()] == [pedidos[0]["id"]]

    cancelados = client.get("/pedidos?status=Cancelado", headers=admin)
    assert [p["id"] for p in cancelados.json()] == [pedidos[0]["id"]]
    assert cancelados.headers["X-Total-Count"] == "1"

    com_carga = client.get("/pedidos?sem_carga=false", headers=admin).json()
    assert [p["id"] for p in com_carga] == [pedidos[1]["id"]]
    assert len(client.get("/pedidos?sem_carga=true", headers=admin).json()) == 4

    assert client.get("/pedidos?limite=0", headers=admin).status_code == 422
    assert client.get("/pedidos?limite=501", headers=admin).status_code == 422
    assert client.get("/pedidos?status=Inexistente", headers=admin).status_code == 422


def test_mensagem_de_transicao_lista_opcoes_na_ordem_do_fluxo(client, admin, novo_pedido):
    pedido = novo_pedido()
    resposta = client.put(f"/pedidos/{pedido['id']}", json={"status": "Entregue"}, headers=admin)
    assert resposta.json()["detail"].endswith("Próximos status permitidos: Em separação, Cancelado.")


def test_status_igual_ao_atual_nao_gera_historico(client, admin, novo_pedido):
    pedido = novo_pedido()
    assert client.put(f"/pedidos/{pedido['id']}", json={"status": "Pendente"}, headers=admin).status_code == 200
    assert len(client.get(f"/pedidos/{pedido['id']}/historico", headers=admin).json()) == 1
