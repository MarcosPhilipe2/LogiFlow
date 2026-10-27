from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import app


def test_inicio_e_status(client):
    assert client.get("/").json()["versao"] == app.version
    assert client.get("/status").json() == {"status": "online"}


def test_banco_conectado(client):
    resposta = client.get("/database/status")
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "conectado"


def test_banco_indisponivel_responde_503_sem_expor_detalhes(client, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'pasta-inexistente' / 'banco.db'}")
    sessao_quebrada = sessionmaker(bind=engine)

    def get_db_quebrado():
        db = sessao_quebrada()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = get_db_quebrado
    resposta = client.get("/database/status")
    engine.dispose()

    assert resposta.status_code == 503
    assert resposta.json()["status"] == "erro"
    assert "detalhes" not in resposta.json()
