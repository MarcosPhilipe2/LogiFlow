"""Cria o primeiro Administrador.

Interativo por padrão. Para instalações automáticas, defina LOGIFLOW_ADMIN_USUARIO,
LOGIFLOW_ADMIN_NOME e LOGIFLOW_ADMIN_SENHA antes de executar.
"""
import os
from getpass import getpass

from app.database import SessionLocal
from app.enums.perfil_usuario import PerfilUsuario
from app.models.usuario import Usuario
from app.services.auth import gerar_hash_senha, normalizar_usuario


def existe_administrador() -> bool:
    with SessionLocal() as db:
        return db.query(Usuario).filter(Usuario.perfil == PerfilUsuario.ADMINISTRADOR.value).count() > 0


def ler_dados() -> tuple[str, str, str, str]:
    if os.getenv("LOGIFLOW_ADMIN_USUARIO"):
        senha = os.getenv("LOGIFLOW_ADMIN_SENHA", "")
        return (
            normalizar_usuario(os.environ["LOGIFLOW_ADMIN_USUARIO"]),
            os.getenv("LOGIFLOW_ADMIN_NOME", "Administrador").strip(),
            senha,
            senha,
        )

    print("\n=== Primeiro Administrador LogiFlow ===\n")
    usuario = normalizar_usuario(input("Usuário: "))
    nome = input("Nome completo: ").strip()
    senha = getpass("Senha (mínimo de 8 caracteres; não aparece ao digitar): ")
    confirmar = getpass("Confirme a senha: ")
    return usuario, nome, senha, confirmar


def criar_administrador() -> bool:
    """Retorna True se um Administrador existe ao final (criado agora ou antes)."""
    db = SessionLocal()
    try:
        quantidade = db.query(Usuario).filter(Usuario.perfil == PerfilUsuario.ADMINISTRADOR.value).count()
        if quantidade > 0:
            print("\nJá existe pelo menos um Administrador cadastrado.")
            return True

        usuario, nome, senha, confirmar = ler_dados()

        if not 3 <= len(usuario) <= 50:
            print("\nErro: o usuário precisa ter entre 3 e 50 caracteres.")
            return False
        if not 2 <= len(nome) <= 150:
            print("\nErro: informe um nome válido.")
            return False
        if not 8 <= len(senha) <= 128:
            print("\nErro: a senha precisa ter entre 8 e 128 caracteres.")
            return False
        if senha != confirmar:
            print("\nErro: as senhas não coincidem.")
            return False
        if db.query(Usuario).filter(Usuario.usuario == usuario).first():
            print("\nErro: esse usuário já está cadastrado.")
            return False

        admin = Usuario(
            usuario=usuario,
            nome=nome,
            senha_hash=gerar_hash_senha(senha),
            perfil=PerfilUsuario.ADMINISTRADOR.value,
            ativo=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print("\nAdministrador criado com sucesso!")
        print(f"ID: {admin.id}")
        print(f"Usuário: {admin.usuario}")
        print(f"Nome: {admin.nome}")
        print(f"Perfil: {admin.perfil}")
        return True
    except Exception as erro:
        db.rollback()
        print("\nNão foi possível criar o Administrador.")
        print(f"Erro: {erro}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    criar_administrador()
