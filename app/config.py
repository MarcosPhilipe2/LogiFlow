import os
from pathlib import Path

from dotenv import load_dotenv
from app.conexao import normalizar_url_banco

RAIZ_PROJETO = Path(__file__).resolve().parent.parent

load_dotenv(RAIZ_PROJETO / ".env")

VERSAO_API = "2.9.0"

DATABASE_URL = normalizar_url_banco(os.getenv("DATABASE_URL", "sqlite:///./logiflow.db"))
if os.getenv("RENDER") and not DATABASE_URL.startswith("postgresql+psycopg://"):
    raise RuntimeError("No Render, configure DATABASE_URL com a conexão PostgreSQL do Supabase.")
if DATABASE_URL.startswith("sqlite:///./"):
    # Caminho relativo vale a partir da pasta do projeto, e não da pasta onde o comando foi executado.
    DATABASE_URL = "sqlite:///" + (RAIZ_PROJETO / DATABASE_URL.removeprefix("sqlite:///./")).as_posix()

def _inteiro(nome: str, padrao: int) -> int:
    return int(os.getenv(nome, str(padrao)))


# Rate limit (ver app/protecao.py e a seção "Capacidade e rate limit" do README).
LIMITE_ATIVO = os.getenv("LIMITE_ATIVO", "true").strip().lower() not in {"0", "false", "nao", "não"}
LIMITE_SIMULTANEAS = _inteiro("LIMITE_SIMULTANEAS", 100)
LIMITE_POR_MINUTO = _inteiro("LIMITE_POR_MINUTO", 300)
LIMITE_RAJADA = _inteiro("LIMITE_RAJADA", 60)
LIMITE_LOGIN_POR_MINUTO = _inteiro("LIMITE_LOGIN_POR_MINUTO", 10)
LIMITE_LOGIN_RAJADA = _inteiro("LIMITE_LOGIN_RAJADA", 5)
LIMITE_LOGINS_SIMULTANEOS = _inteiro("LIMITE_LOGINS_SIMULTANEOS", 10)
LIMITE_ESCRITAS_NA_FILA = _inteiro("LIMITE_ESCRITAS_NA_FILA", 20)

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

# Valor de exemplo do .env.example: é público, então nunca pode ser usado de verdade.
_CHAVE_DE_EXEMPLO = "gere_uma_chave_secreta"

if len(JWT_SECRET_KEY) < 32 or JWT_SECRET_KEY == _CHAVE_DE_EXEMPLO:
    raise RuntimeError(
        "JWT_SECRET_KEY ausente ou fraca no arquivo .env (mínimo de 32 caracteres). "
        'Gere uma com: python -c "import secrets; print(secrets.token_hex(32))"'
    )
