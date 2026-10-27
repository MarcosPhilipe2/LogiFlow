from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.usuario import MensagemResposta, MinhaSenhaAtualizar, TokenResposta, UsuarioResposta
from app.services.auth import (
    autenticar_usuario,
    criar_token_acesso,
    gerar_hash_senha,
    obter_usuario_atual,
    verificar_senha,
)

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login", response_model=TokenResposta)
def login(
    dados: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    usuario = autenticar_usuario(db, dados.username, dados.password)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResposta(
        access_token=criar_token_acesso(usuario),
        token_type="bearer",
    )


@router.get("/me", response_model=UsuarioResposta)
def meus_dados(usuario: Usuario = Depends(obter_usuario_atual)):
    return usuario


@router.patch("/senha", response_model=MensagemResposta)
def alterar_minha_senha(
    dados: MinhaSenhaAtualizar,
    usuario: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db),
):
    if not verificar_senha(dados.senha_atual, usuario.senha_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A senha atual está incorreta.")
    if dados.nova_senha == dados.senha_atual:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A nova senha deve ser diferente da atual.")

    usuario.senha_hash = gerar_hash_senha(dados.nova_senha)
    db.commit()
    return MensagemResposta(mensagem="Senha alterada com sucesso. Faça login novamente com a nova senha.")
