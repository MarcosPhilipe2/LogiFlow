"""Deixa o LogiFlow pronto para rodar. Chamado pelo iniciar.bat a cada inicialização.

1. cria o .env com uma chave JWT nova, se ainda não existir;
2. aplica as migrations do banco;
3. garante que exista um Administrador (pergunta os dados na primeira vez);
4. oferece carregar dados de demonstração quando o banco está vazio.

Variáveis opcionais para instalação sem perguntas:
    LOGIFLOW_ADMIN_USUARIO / LOGIFLOW_ADMIN_NOME / LOGIFLOW_ADMIN_SENHA
    LOGIFLOW_DEMO=S (carrega a demonstração) ou N (não carrega)
"""
import os
import secrets
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_ENV = RAIZ / ".env"
EXEMPLO_ENV = RAIZ / ".env.example"
TENTATIVAS_ADMIN = 3


def criar_env_se_necessario() -> None:
    if ARQUIVO_ENV.exists():
        return
    conteudo = EXEMPLO_ENV.read_text(encoding="utf-8").replace("gere_uma_chave_secreta", secrets.token_hex(32))
    ARQUIVO_ENV.write_text(conteudo, encoding="utf-8")
    print("Arquivo .env criado com uma chave JWT nova.")


def aplicar_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    config = Config(str(RAIZ / "alembic.ini"))
    config.set_main_option("script_location", str(RAIZ / "alembic"))
    command.upgrade(config, "head")


def garantir_administrador() -> bool:
    from scripts.criar_admin import criar_administrador, existe_administrador

    if existe_administrador():
        return True
    for _ in range(TENTATIVAS_ADMIN):
        if criar_administrador():
            return True
        if os.getenv("LOGIFLOW_ADMIN_USUARIO"):
            break  # dados vieram de variáveis de ambiente; repetir daria o mesmo erro
        print("Vamos tentar novamente.")
    return False


def oferecer_demonstracao() -> None:
    from app.database import SessionLocal
    from app.models.pedido import Pedido

    with SessionLocal() as db:
        if db.query(Pedido).count() > 0:
            return

    resposta = os.getenv("LOGIFLOW_DEMO")
    if resposta is None:
        if not sys.stdin.isatty():
            return
        resposta = input("\nO banco está vazio. Carregar dados de demonstração? (S/N): ")
    if resposta.strip().upper().startswith("S"):
        from scripts.popular_demo import main as popular

        popular()


def main() -> int:
    criar_env_se_necessario()  # precisa vir antes de qualquer import de app.*
    aplicar_migrations()
    if not garantir_administrador():
        print("\n[ERRO] Nenhum Administrador foi criado. Execute novamente para tentar outra vez.")
        return 1
    oferecer_demonstracao()
    return 0


if __name__ == "__main__":
    sys.exit(main())
