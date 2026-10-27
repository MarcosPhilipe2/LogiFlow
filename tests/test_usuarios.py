USUARIO = {"usuario": "  Maria.Silva ", "nome": "  Maria Silva ", "senha": "senha-forte-123", "perfil": "Operação"}


def id_do_usuario(client, admin, login):
    usuarios = client.get("/usuarios", headers=admin).json()
    return next(u["id"] for u in usuarios if u["usuario"] == login)


def test_criar_listar_e_consultar(client, admin, login):
    resposta = client.post("/usuarios", json=USUARIO, headers=admin)
    assert resposta.status_code == 201
    criado = resposta.json()
    assert criado["usuario"] == "maria.silva"
    assert criado["nome"] == "Maria Silva"
    assert criado["ativo"] is True
    assert "senha_hash" not in criado

    assert login("maria.silva", "senha-forte-123").status_code == 200
    assert client.post("/usuarios", json=USUARIO | {"usuario": "MARIA.SILVA"}, headers=admin).status_code == 409

    logins = [u["usuario"] for u in client.get("/usuarios", headers=admin).json()]
    assert logins == ["admin", "operador", "consulta", "maria.silva"]
    assert client.get(f"/usuarios/{criado['id']}", headers=admin).json()["usuario"] == "maria.silva"
    assert client.get("/usuarios/999", headers=admin).status_code == 404


def test_validacoes_de_cadastro(client, admin):
    assert client.post("/usuarios", json=USUARIO | {"senha": "curta"}, headers=admin).status_code == 422
    assert client.post("/usuarios", json=USUARIO | {"usuario": "  a  "}, headers=admin).status_code == 422
    assert client.post("/usuarios", json=USUARIO | {"perfil": "Root"}, headers=admin).status_code == 422


def test_senha_nao_e_alterada_por_espacos(client, admin, login):
    corpo = USUARIO | {"usuario": "joao", "senha": "  senha com espacos  "}
    assert client.post("/usuarios", json=corpo, headers=admin).status_code == 201
    assert login("joao", "  senha com espacos  ").status_code == 200
    assert login("joao", "senha com espacos").status_code == 401


def test_administrador_nao_remove_o_proprio_acesso(client, admin):
    meu_id = client.get("/auth/me", headers=admin).json()["id"]
    assert client.patch(f"/usuarios/{meu_id}/perfil", json={"perfil": "Consulta"}, headers=admin).status_code == 409
    assert client.patch(f"/usuarios/{meu_id}/status", json={"ativo": False}, headers=admin).status_code == 409
    assert client.patch(f"/usuarios/{meu_id}/perfil", json={"perfil": "Administrador"}, headers=admin).status_code == 200


def test_alterar_perfil_vale_imediatamente(client, admin, consulta):
    corpo = {"numero_pedido": "P-1", "cliente": "Cliente", "cidade": "Cidade", "uf": "SP"}
    assert client.post("/pedidos", json=corpo, headers=consulta).status_code == 403

    consulta_id = client.get("/auth/me", headers=consulta).json()["id"]
    resposta = client.patch(f"/usuarios/{consulta_id}/perfil", json={"perfil": "Operação"}, headers=admin)
    assert resposta.status_code == 200
    assert resposta.json()["perfil"] == "Operação"
    assert client.post("/pedidos", json=corpo, headers=consulta).status_code == 201


def test_alterar_senha(client, admin, login):
    operador_id = id_do_usuario(client, admin, "operador")
    resposta = client.patch(f"/usuarios/{operador_id}/senha", json={"nova_senha": "nova-senha-123"}, headers=admin)
    assert resposta.status_code == 200
    assert "operador" in resposta.json()["mensagem"]

    assert login("operador").status_code == 401
    assert login("operador", "nova-senha-123").status_code == 200
    assert client.patch(f"/usuarios/{operador_id}/senha", json={"nova_senha": "curta"}, headers=admin).status_code == 422


def test_reativar_usuario(client, admin, login):
    operador_id = id_do_usuario(client, admin, "operador")
    client.patch(f"/usuarios/{operador_id}/status", json={"ativo": False}, headers=admin)
    assert login("operador").status_code == 401
    client.patch(f"/usuarios/{operador_id}/status", json={"ativo": True}, headers=admin)
    assert login("operador").status_code == 200
