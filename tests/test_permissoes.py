PEDIDO = {"numero_pedido": "NOVO-1", "cliente": "Cliente", "cidade": "Cidade", "uf": "SP"}
CARGA = {"numero_carga": "NOVA-1", "transportadora": "Transportadora"}


def test_consulta_apenas_le(client, consulta, novo_pedido, nova_carga):
    pedido = novo_pedido()
    carga = nova_carga()

    assert client.get("/pedidos", headers=consulta).status_code == 200
    assert client.get(f"/pedidos/{pedido['id']}", headers=consulta).status_code == 200
    assert client.get(f"/cargas/{carga['id']}", headers=consulta).status_code == 200
    assert client.get("/dashboard/resumo", headers=consulta).status_code == 200

    assert client.post("/pedidos", json=PEDIDO, headers=consulta).status_code == 403
    assert client.put(f"/pedidos/{pedido['id']}", json={"cliente": "Outro"}, headers=consulta).status_code == 403
    assert client.delete(f"/pedidos/{pedido['id']}", headers=consulta).status_code == 403
    assert client.post("/cargas", json=CARGA, headers=consulta).status_code == 403
    assert client.post(f"/cargas/{carga['id']}/pedidos/{pedido['id']}", headers=consulta).status_code == 403
    assert client.delete(f"/cargas/{carga['id']}/pedidos/{pedido['id']}", headers=consulta).status_code == 403
    assert client.get("/usuarios", headers=consulta).status_code == 403


def test_operacao_cria_altera_e_desvincula_mas_nao_exclui(client, operador, novo_pedido, nova_carga):
    pedido = novo_pedido()
    carga = nova_carga()

    assert client.post("/pedidos", json=PEDIDO, headers=operador).status_code == 201
    assert client.put(f"/pedidos/{pedido['id']}", json={"cliente": "Outro"}, headers=operador).status_code == 200
    assert client.post("/cargas", json=CARGA, headers=operador).status_code == 201
    assert client.put(f"/cargas/{carga['id']}", json={"motorista": "José"}, headers=operador).status_code == 200
    assert client.post(f"/cargas/{carga['id']}/pedidos/{pedido['id']}", headers=operador).status_code == 200
    assert client.delete(f"/cargas/{carga['id']}/pedidos/{pedido['id']}", headers=operador).status_code == 200

    assert client.delete(f"/pedidos/{pedido['id']}", headers=operador).status_code == 403
    assert client.delete(f"/cargas/{carga['id']}", headers=operador).status_code == 403
    assert client.get("/usuarios", headers=operador).status_code == 403


def test_administrador_exclui_pedidos_e_cargas(client, admin, novo_pedido, nova_carga):
    pedido = novo_pedido()
    carga = nova_carga()

    assert client.delete(f"/pedidos/{pedido['id']}", headers=admin).status_code == 200
    assert client.get(f"/pedidos/{pedido['id']}", headers=admin).status_code == 404
    assert client.delete(f"/cargas/{carga['id']}", headers=admin).status_code == 200
    assert client.get(f"/cargas/{carga['id']}", headers=admin).status_code == 404
