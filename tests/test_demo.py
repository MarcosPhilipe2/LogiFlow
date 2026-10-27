from scripts.popular_demo import popular


def test_dados_de_demonstracao_seguem_as_regras(client, fabrica_sessao, admin):
    with fabrica_sessao() as db:
        popular(db)

    resumo = client.get("/dashboard/resumo", headers=admin).json()
    assert resumo["cargas"] == {
        "total": 7, "planejadas": 1, "em_carregamento": 1, "carregadas": 1,
        "em_transporte": 1, "finalizadas": 2, "canceladas": 1,
    }
    # Pendentes: 2 da carga planejada + 2 liberados da carga cancelada + 5 avulsos.
    assert resumo["pedidos"] == {
        "total": 30, "pendentes": 9, "em_separacao": 5, "carregados": 3,
        "em_transporte": 4, "entregues": 7, "cancelados": 2, "sem_carga": 11,
    }

    finalizada = client.get("/cargas?status=Finalizada", headers=admin).json()[0]
    historico = client.get(f"/cargas/{finalizada['id']}/historico", headers=admin).json()
    assert [h["status_novo"] for h in historico] == [
        "Planejada", "Em carregamento", "Carregada", "Em transporte", "Finalizada",
    ]
