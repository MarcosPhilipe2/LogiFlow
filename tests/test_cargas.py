import pytest

CARGA = {"numero_carga": "CAR-X", "transportadora": "Transportadora"}


def resumo_historico(historico):
    return [(h["status_anterior"], h["status_novo"], h["origem"]) for h in historico]


def test_criar_carga_normaliza_campos(client, admin):
    corpo = {"numero_carga": " car-1 ", "transportadora": "  Rápido Sul  ", "veiculo": "ABC1D23"}
    resposta = client.post("/cargas", json=corpo, headers=admin)
    assert resposta.status_code == 201
    carga = resposta.json()
    assert carga["numero_carga"] == "CAR-1"
    assert carga["transportadora"] == "Rápido Sul"
    assert carga["status"] == "Planejada"
    assert carga["peso_total"] == 0


def test_numero_de_carga_duplicado(client, admin, nova_carga):
    nova_carga(numero_carga="CAR-1")
    assert client.post("/cargas", json=CARGA | {"numero_carga": "car-1"}, headers=admin).status_code == 409


def test_carga_sempre_nasce_planejada(client, admin):
    assert client.post("/cargas", json=CARGA | {"status": "Finalizada"}, headers=admin).status_code == 422
    assert client.post("/cargas", json=CARGA | {"status": "Planejada"}, headers=admin).status_code == 201


def test_carga_inexistente(client, admin, novo_pedido):
    pedido = novo_pedido()
    assert client.get("/cargas/999", headers=admin).status_code == 404
    assert client.put("/cargas/999", json={"motorista": "José"}, headers=admin).status_code == 404
    assert client.get("/cargas/999/pedidos", headers=admin).status_code == 404
    assert client.get("/cargas/999/historico", headers=admin).status_code == 404
    assert client.post(f"/cargas/999/pedidos/{pedido['id']}", headers=admin).status_code == 404
    assert client.delete("/cargas/999", headers=admin).status_code == 404


def test_peso_total_e_pedidos_da_carga(client, admin, novo_pedido, nova_carga, vincular):
    carga = nova_carga()
    primeiro = novo_pedido(peso=10.25)
    segundo = novo_pedido(peso=4.5)
    vincular(carga["id"], primeiro["id"])
    resposta = vincular(carga["id"], segundo["id"])
    assert resposta["peso_total"] == 14.75

    pedidos = client.get(f"/cargas/{carga['id']}/pedidos", headers=admin).json()
    assert [p["id"] for p in pedidos] == [primeiro["id"], segundo["id"]]
    assert all(p["carga_id"] == carga["id"] for p in pedidos)


def test_fluxo_completo_sincroniza_pedidos(client, admin, novo_pedido, nova_carga, vincular, avancar_carga):
    carga = nova_carga()
    pedido = novo_pedido()
    vincular(carga["id"], pedido["id"])

    def status_do_pedido():
        return client.get(f"/pedidos/{pedido['id']}", headers=admin).json()["status"]

    assert status_do_pedido() == "Pendente"
    for status_carga, status_pedido in [
        ("Em carregamento", "Em separação"),
        ("Carregada", "Carregado"),
        ("Em transporte", "Em transporte"),
        ("Finalizada", "Entregue"),
    ]:
        avancar_carga(carga["id"], status_carga)
        assert status_do_pedido() == status_pedido

    historico_pedido = client.get(f"/pedidos/{pedido['id']}/historico", headers=admin).json()
    assert resumo_historico(historico_pedido) == [
        (None, "Pendente", "criacao"),
        ("Pendente", "Em separação", "sincronizacao_carga"),
        ("Em separação", "Carregado", "sincronizacao_carga"),
        ("Carregado", "Em transporte", "sincronizacao_carga"),
        ("Em transporte", "Entregue", "sincronizacao_carga"),
    ]
    historico_carga = client.get(f"/cargas/{carga['id']}/historico", headers=admin).json()
    assert resumo_historico(historico_carga) == [
        (None, "Planejada", "criacao"),
        ("Planejada", "Em carregamento", "manual"),
        ("Em carregamento", "Carregada", "manual"),
        ("Carregada", "Em transporte", "manual"),
        ("Em transporte", "Finalizada", "manual"),
    ]


def test_vincular_em_carga_em_carregamento_separa_pedido(client, admin, novo_pedido, nova_carga, vincular, avancar_carga):
    carga = nova_carga()
    vincular(carga["id"], novo_pedido()["id"])
    avancar_carga(carga["id"], "Em carregamento")

    pedido = novo_pedido()
    vincular(carga["id"], pedido["id"])
    assert client.get(f"/pedidos/{pedido['id']}", headers=admin).json()["status"] == "Em separação"
    historico = client.get(f"/pedidos/{pedido['id']}/historico", headers=admin).json()
    assert resumo_historico(historico)[-1] == ("Pendente", "Em separação", "vinculo_carga")


def test_regras_de_vinculo(client, admin, novo_pedido, nova_carga, vincular, avancar_carga, mudar_status_pedido):
    carga = nova_carga()
    outra_carga = nova_carga()
    pedido = novo_pedido()

    vincular(carga["id"], pedido["id"])
    vincular(carga["id"], pedido["id"])  # repetir o vínculo na mesma carga é permitido
    resposta = client.post(f"/cargas/{outra_carga['id']}/pedidos/{pedido['id']}", headers=admin)
    assert resposta.status_code == 409
    assert "outra carga" in resposta.json()["detail"]

    cancelado = novo_pedido()
    mudar_status_pedido(cancelado["id"], "Cancelado")
    assert client.post(f"/cargas/{outra_carga['id']}/pedidos/{cancelado['id']}", headers=admin).status_code == 409

    avancar_carga(carga["id"], "Em carregamento", "Carregada")
    resposta = client.post(f"/cargas/{carga['id']}/pedidos/{novo_pedido()['id']}", headers=admin)
    assert resposta.status_code == 409
    assert "Planejada" in resposta.json()["detail"]

    assert client.post(f"/cargas/{carga['id']}/pedidos/999", headers=admin).status_code == 404


def test_regras_de_desvinculo(client, admin, novo_pedido, nova_carga, vincular, avancar_carga):
    carga = nova_carga()
    outra_carga = nova_carga()
    pedido = novo_pedido()
    vincular(carga["id"], pedido["id"])

    resposta = client.delete(f"/cargas/{outra_carga['id']}/pedidos/{pedido['id']}", headers=admin)
    assert resposta.status_code == 409
    assert "não pertence" in resposta.json()["detail"]

    avancar_carga(carga["id"], "Em carregamento", "Carregada", "Em transporte")
    assert client.delete(f"/cargas/{carga['id']}/pedidos/{pedido['id']}", headers=admin).status_code == 409

    pedido_livre = novo_pedido()
    vincular(outra_carga["id"], pedido_livre["id"])
    assert client.delete(f"/cargas/{outra_carga['id']}/pedidos/{pedido_livre['id']}", headers=admin).status_code == 200
    assert client.get(f"/pedidos/{pedido_livre['id']}", headers=admin).json()["carga_id"] is None
    assert client.get(f"/cargas/{outra_carga['id']}", headers=admin).json()["peso_total"] == 0


def test_carga_nao_sai_sem_pedidos(client, admin, nova_carga, avancar_carga):
    carga = nova_carga()
    avancar_carga(carga["id"], "Em carregamento", "Carregada")
    resposta = client.put(f"/cargas/{carga['id']}", json={"status": "Em transporte"}, headers=admin)
    assert resposta.status_code == 409
    assert "pelo menos um pedido" in resposta.json()["detail"]


def test_transicao_invalida_de_carga(client, admin, nova_carga):
    carga = nova_carga()
    resposta = client.put(f"/cargas/{carga['id']}", json={"status": "Finalizada"}, headers=admin)
    assert resposta.status_code == 409
    assert resposta.json()["detail"].endswith("Próximos status permitidos: Em carregamento, Cancelada.")


def test_status_igual_ao_atual_nao_gera_historico(client, admin, nova_carga):
    carga = nova_carga()
    assert client.put(f"/cargas/{carga['id']}", json={"status": "Planejada"}, headers=admin).status_code == 200
    assert len(client.get(f"/cargas/{carga['id']}/historico", headers=admin).json()) == 1


def test_atualizar_carga_normaliza_e_aceita_data_de_saida(client, admin, nova_carga):
    carga = nova_carga()
    corpo = {"numero_carga": " car-nova ", "transportadora": "  Nova Transp  ", "data_saida": "2026-10-28T08:30:00"}
    resposta = client.put(f"/cargas/{carga['id']}", json=corpo, headers=admin)
    assert resposta.status_code == 200, resposta.text
    atualizada = resposta.json()
    assert atualizada["numero_carga"] == "CAR-NOVA"
    assert atualizada["transportadora"] == "Nova Transp"
    assert atualizada["data_saida"] == "2026-10-28T08:30:00"


@pytest.mark.parametrize("campo", ["numero_carga", "transportadora", "status"])
def test_atualizar_carga_rejeita_nulo_em_campo_obrigatorio(client, admin, nova_carga, campo):
    carga = nova_carga()
    assert client.put(f"/cargas/{carga['id']}", json={campo: None}, headers=admin).status_code == 422


def test_atualizar_carga_permite_limpar_campos_opcionais(client, admin, nova_carga):
    carga = nova_carga(veiculo="ABC1D23", motorista="José")
    resposta = client.put(f"/cargas/{carga['id']}", json={"veiculo": None, "motorista": None}, headers=admin)
    assert resposta.status_code == 200
    assert resposta.json()["veiculo"] is None
    assert resposta.json()["motorista"] is None


def test_atualizar_carga_para_numero_existente(client, admin, nova_carga):
    nova_carga(numero_carga="CAR-A")
    outra = nova_carga(numero_carga="CAR-B")
    resposta = client.put(f"/cargas/{outra['id']}", json={"numero_carga": "car-a"}, headers=admin)
    assert resposta.status_code == 409
    assert "Já existe uma carga" in resposta.json()["detail"]


def test_excluir_carga_exige_que_esteja_vazia(client, admin, novo_pedido, nova_carga, vincular):
    carga = nova_carga()
    pedido = novo_pedido()
    vincular(carga["id"], pedido["id"])

    assert client.delete(f"/cargas/{carga['id']}", headers=admin).status_code == 409
    assert client.delete(f"/cargas/{carga['id']}/pedidos/{pedido['id']}", headers=admin).status_code == 200
    assert client.delete(f"/cargas/{carga['id']}", headers=admin).status_code == 200
    assert client.get(f"/cargas/{carga['id']}", headers=admin).status_code == 404


def test_desvincular_devolve_pedido_para_pendente(client, admin, novo_pedido, nova_carga, vincular, avancar_carga):
    carga = nova_carga()
    pedido = novo_pedido()
    vincular(carga["id"], pedido["id"])
    vincular(carga["id"], novo_pedido()["id"])
    avancar_carga(carga["id"], "Em carregamento", "Carregada")

    assert client.delete(f"/cargas/{carga['id']}/pedidos/{pedido['id']}", headers=admin).status_code == 200
    liberado = client.get(f"/pedidos/{pedido['id']}", headers=admin).json()
    assert liberado["status"] == "Pendente"
    assert liberado["carga_id"] is None
    historico = client.get(f"/pedidos/{pedido['id']}/historico", headers=admin).json()
    assert resumo_historico(historico)[-1] == ("Carregado", "Pendente", "desvinculo_carga")


def test_cancelar_carga_libera_os_pedidos(client, admin, novo_pedido, nova_carga, vincular, avancar_carga):
    carga = nova_carga()
    pedidos = [novo_pedido(), novo_pedido()]
    for pedido in pedidos:
        vincular(carga["id"], pedido["id"])
    avancar_carga(carga["id"], "Em carregamento")

    resposta = client.put(f"/cargas/{carga['id']}", json={"status": "Cancelada"}, headers=admin)
    assert resposta.status_code == 200
    assert resposta.json()["peso_total"] == 0
    assert client.get(f"/cargas/{carga['id']}/pedidos", headers=admin).json() == []

    for pedido in pedidos:
        liberado = client.get(f"/pedidos/{pedido['id']}", headers=admin).json()
        assert (liberado["status"], liberado["carga_id"]) == ("Pendente", None)
        historico = client.get(f"/pedidos/{pedido['id']}/historico", headers=admin).json()
        assert resumo_historico(historico)[-1] == ("Em separação", "Pendente", "cancelamento_carga")

    # Liberados, os pedidos podem entrar em outra carga.
    vincular(nova_carga()["id"], pedidos[0]["id"])


def test_listagem_de_cargas_com_filtro_e_paginacao(client, admin, nova_carga, avancar_carga):
    cargas = [nova_carga() for _ in range(3)]
    avancar_carga(cargas[0]["id"], "Cancelada")

    resposta = client.get("/cargas?limite=1", headers=admin)
    assert resposta.headers["X-Total-Count"] == "3"
    assert [c["id"] for c in resposta.json()] == [cargas[2]["id"]]

    planejadas = client.get("/cargas?status=Planejada", headers=admin).json()
    assert [c["id"] for c in planejadas] == [cargas[2]["id"], cargas[1]["id"]]
