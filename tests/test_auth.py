from app.services import auth


def test_login_normaliza_usuario_e_retorna_dados(client, login):
    resposta = login("  ADMIN ")
    assert resposta.status_code == 200
    assert resposta.json()["token_type"] == "bearer"

    token = resposta.json()["access_token"]
    dados = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert dados["usuario"] == "admin"
    assert dados["perfil"] == "Administrador"
    assert "senha_hash" not in dados


def test_login_invalido(login):
    assert login("admin", "senha-errada").status_code == 401
    assert login("ninguem").status_code == 401


def test_rotas_protegidas_exigem_token(client):
    for rota in ["/auth/me", "/pedidos", "/cargas", "/dashboard/resumo", "/usuarios"]:
        assert client.get(rota).status_code == 401, rota
    assert client.get("/pedidos", headers={"Authorization": "Bearer invalido"}).status_code == 401


def test_usuario_desativado_perde_acesso(client, admin, operador, login):
    operador_id = client.get("/auth/me", headers=operador).json()["id"]
    resposta = client.patch(f"/usuarios/{operador_id}/status", json={"ativo": False}, headers=admin)
    assert resposta.status_code == 200

    assert client.get("/pedidos", headers=operador).status_code == 403
    assert login("operador").status_code == 401


def test_login_sempre_verifica_hash_para_nao_revelar_usuarios(login, monkeypatch):
    """Sem isso, a resposta para um usuário inexistente é bem mais rápida (enumeração por tempo)."""
    chamadas = []
    verificar_original = auth.password_hash.verify

    def espiao(*args, **kwargs):
        chamadas.append(args)
        return verificar_original(*args, **kwargs)

    monkeypatch.setattr(auth.password_hash, "verify", espiao)

    assert login("ninguem").status_code == 401
    assert len(chamadas) == 1


def test_usuario_troca_a_propria_senha(client, consulta, login):
    url = "/auth/senha"
    assert client.patch(url, json={"senha_atual": "errada", "nova_senha": "nova-senha-123"}, headers=consulta).status_code == 400
    assert client.patch(url, json={"senha_atual": "senha-de-teste", "nova_senha": "senha-de-teste"}, headers=consulta).status_code == 400
    assert client.patch(url, json={"senha_atual": "senha-de-teste", "nova_senha": "curta"}, headers=consulta).status_code == 422

    resposta = client.patch(url, json={"senha_atual": "senha-de-teste", "nova_senha": "nova-senha-123"}, headers=consulta)
    assert resposta.status_code == 200

    assert client.get("/auth/me", headers=consulta).status_code == 401
    assert login("consulta").status_code == 401
    assert login("consulta", "nova-senha-123").status_code == 200


def test_senha_redefinida_pelo_admin_derruba_tokens_antigos(client, admin, operador):
    operador_id = client.get("/auth/me", headers=operador).json()["id"]
    client.patch(f"/usuarios/{operador_id}/senha", json={"nova_senha": "outra-senha-123"}, headers=admin)
    assert client.get("/pedidos", headers=operador).status_code == 401
    assert client.get("/pedidos", headers=admin).status_code == 200


def test_token_sem_versao_da_senha_e_recusado(client):
    import jwt

    from app.config import JWT_ALGORITHM, JWT_SECRET_KEY

    token_antigo = jwt.encode({"sub": "1", "exp": 9999999999}, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token_antigo}"}).status_code == 401
