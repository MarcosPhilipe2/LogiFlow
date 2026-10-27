"""Aplica migrations e inicia um processo da API no container."""
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


def preparar() -> None:
    from scripts.preparar import aplicar_migrations
    from scripts.criar_admin import criar_administrador, existe_administrador

    aplicar_migrations()
    if not existe_administrador():
        if not os.getenv("LOGIFLOW_ADMIN_USUARIO") or not os.getenv("LOGIFLOW_ADMIN_SENHA"):
            raise RuntimeError(
                "Primeira instalação: configure LOGIFLOW_ADMIN_USUARIO e "
                "LOGIFLOW_ADMIN_SENHA no ambiente do container."
            )
        if not criar_administrador():
            raise RuntimeError("Não foi possível cadastrar o primeiro administrador.")


def main() -> None:
    os.chdir(RAIZ)
    preparar()
    # A senha inicial não precisa ser herdada pelo servidor após o cadastro.
    os.environ.pop("LOGIFLOW_ADMIN_SENHA", None)
    porta = int(os.getenv("PORT", "8000"))
    if not 1 <= porta <= 65535:
        raise ValueError("PORT precisa estar entre 1 e 65535.")
    os.execv(sys.executable, [
        sys.executable, "-m", "uvicorn", "app.main:app",
        "--host", "0.0.0.0", "--port", str(porta), "--workers", "1",
        "--no-proxy-headers",
    ])


if __name__ == "__main__":
    main()
