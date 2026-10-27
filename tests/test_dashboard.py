from datetime import date, timedelta


def test_resumo_vazio(client, consulta):
    resumo = client.get("/dashboard/resumo", headers=consulta).json()
    assert all(valor == 0 for valor in resumo["pedidos"].values())
    assert all(valor == 0 for valor in resumo["cargas"].values())
    assert all(valor == 0 for valor in resumo["operacao"].values())


def test_resumo(client, consulta, novo_pedido, nova_carga, vincular, avancar_carga, mudar_status_pedido):
    vinculado = novo_pedido(peso=10, valor_total=100)
    novo_pedido(peso=5.5, valor_total=50.5)
    cancelado = novo_pedido(peso=1, valor_total=1)
    mudar_status_pedido(cancelado["id"], "Cancelado")

    carga = nova_carga()
    cancelada = nova_carga()
    vincular(carga["id"], vinculado["id"])
    avancar_carga(carga["id"], "Em carregamento")
    avancar_carga(cancelada["id"], "Cancelada")

    resumo = client.get("/dashboard/resumo", headers=consulta).json()
    assert resumo["pedidos"] == {
        "total": 3, "pendentes": 1, "em_separacao": 1, "carregados": 0,
        "em_transporte": 0, "entregues": 0, "cancelados": 1, "sem_carga": 2,
    }
    assert resumo["cargas"] == {
        "total": 2, "planejadas": 0, "em_carregamento": 1, "carregadas": 0,
        "em_transporte": 0, "finalizadas": 0, "canceladas": 1,
    }
    assert resumo["operacao"] == {
        "peso_total_pedidos": 16.5,
        "peso_vinculado_cargas": 10.0,
        "valor_total_pedidos": 151.5,
    }


def test_pedidos_por_cidade(client, consulta, novo_pedido):
    novo_pedido(cidade="Campinas", uf="SP", peso=1, valor_total=10)
    novo_pedido(cidade="Campinas", uf="SP", peso=2, valor_total=20)
    novo_pedido(cidade="Niterói", uf="RJ", peso=3, valor_total=30)

    resultado = client.get("/dashboard/pedidos-por-cidade", headers=consulta).json()
    assert resultado == [
        {"cidade": "Campinas", "uf": "SP", "quantidade": 2, "peso_total": 3.0, "valor_total": 30.0},
        {"cidade": "Niterói", "uf": "RJ", "quantidade": 1, "peso_total": 3.0, "valor_total": 30.0},
    ]
    assert len(client.get("/dashboard/pedidos-por-cidade?limite=1", headers=consulta).json()) == 1
    assert client.get("/dashboard/pedidos-por-cidade?limite=0", headers=consulta).status_code == 422


def test_cargas_por_transportadora(client, consulta, novo_pedido, nova_carga, vincular):
    carga = nova_carga(transportadora="Alfa")
    nova_carga(transportadora="Alfa")
    nova_carga(transportadora="Beta")
    vincular(carga["id"], novo_pedido(peso=2)["id"])
    vincular(carga["id"], novo_pedido(peso=3)["id"])

    resultado = client.get("/dashboard/cargas-por-transportadora", headers=consulta).json()
    assert resultado == [
        {"transportadora": "Alfa", "quantidade_cargas": 2, "quantidade_pedidos": 2, "peso_total": 5.0},
        {"transportadora": "Beta", "quantidade_cargas": 1, "quantidade_pedidos": 0, "peso_total": 0.0},
    ]


def test_pedidos_por_dia(client, consulta, novo_pedido):
    novo_pedido()
    novo_pedido()

    resultado = client.get("/dashboard/pedidos-por-dia?dias=3", headers=consulta).json()
    hoje = date.today()
    assert resultado == [
        {"data": (hoje - timedelta(days=2)).isoformat(), "quantidade": 0},
        {"data": (hoje - timedelta(days=1)).isoformat(), "quantidade": 0},
        {"data": hoje.isoformat(), "quantidade": 2},
    ]
    assert client.get("/dashboard/pedidos-por-dia?dias=0", headers=consulta).status_code == 422
