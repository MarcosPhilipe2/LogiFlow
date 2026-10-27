"""Gera configuração privada para Docker sem instalar dependências Python."""
import os
import secrets
from getpass import getpass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def criar_configuracao(usuario: str, nome: str, senha: str, confirmar: str) -> str:
    usuario, nome = usuario.strip().lower(), nome.strip()
    if not 3 <= len(usuario) <= 50 or not 2 <= len(nome) <= 150:
        raise ValueError("Login deve ter 3 a 50 caracteres; nome, 2 a 150.")
    if not 8 <= len(senha) <= 128:
        raise ValueError("A senha precisa ter de 8 a 128 caracteres.")
    if senha != confirmar:
        raise ValueError("As senhas não coincidem.")
    if any(c in valor for valor in (usuario, nome, senha) for c in '\r\n\0'):
        raise ValueError("Os campos não podem conter quebras de linha ou caracteres nulos.")
    return (
        f"JWT_SECRET_KEY={secrets.token_hex(32)}\n"
        "JWT_ALGORITHM=HS256\nJWT_EXPIRE_MINUTES=60\n"
        f"LOGIFLOW_ADMIN_USUARIO={usuario}\nLOGIFLOW_ADMIN_NOME={nome}\n"
        f"LOGIFLOW_ADMIN_SENHA={senha}\nLIMITE_ATIVO=true\n"
    )


def main() -> int:
    destino = RAIZ / '.env.docker'
    if destino.exists():
        print('.env.docker já existe. Configuração preservada.')
        return 0
    print('Configuração Docker — primeiro administrador (sem dados de demonstração).')
    try:
        conteudo = criar_configuracao(
            input('Login do administrador: '), input('Nome completo: '),
            getpass('Senha (8 a 128 caracteres): '), getpass('Confirme a senha: '),
        )
        descritor = os.open(destino, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descritor, 'w', encoding='utf-8', newline='\n') as arquivo:
            arquivo.write(conteudo)
    except (ValueError, OSError, EOFError, KeyboardInterrupt) as erro:
        print(f'Configuração não criada: {erro}')
        return 1
    print('Configuração criada. Execute: docker compose up -d --build')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
