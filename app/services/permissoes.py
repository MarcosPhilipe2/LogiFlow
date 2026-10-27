from fastapi import Depends, HTTPException, status

from app.enums.perfil_usuario import PerfilUsuario
from app.models.usuario import Usuario
from app.services.auth import obter_usuario_atual


def exigir_perfil(*perfis: PerfilUsuario, mensagem: str):
    """Cria uma dependência que só deixa passar usuários com um dos perfis informados."""
    permitidos = {perfil.value for perfil in perfis}

    def verificar_perfil(usuario: Usuario = Depends(obter_usuario_atual)) -> Usuario:
        if usuario.perfil not in permitidos:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=mensagem)
        return usuario

    return verificar_perfil


# Leitura fica liberada para qualquer usuário autenticado (dependência aplicada no main.py).
exigir_operacao = exigir_perfil(
    PerfilUsuario.ADMINISTRADOR,
    PerfilUsuario.OPERACAO,
    mensagem="Seu perfil não possui permissão para realizar esta operação.",
)

exigir_administrador = exigir_perfil(
    PerfilUsuario.ADMINISTRADOR,
    mensagem="Esta operação exige perfil de Administrador.",
)
