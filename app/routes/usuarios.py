from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums.perfil_usuario import PerfilUsuario
from app.models.usuario import Usuario
from app.routes.comum import usuario_ou_404
from app.schemas.usuario import (
    MensagemResposta,
    UsuarioCriar,
    UsuarioPerfilAtualizar,
    UsuarioResposta,
    UsuarioSenhaAtualizar,
    UsuarioStatusAtualizar,
)
from app.services.auth import buscar_usuario_por_login, gerar_hash_senha
from app.services.erros import RegraNegocioError
from app.services.permissoes import exigir_administrador

router = APIRouter(
    prefix="/usuarios",
    tags=["Usuários"],
    dependencies=[Depends(exigir_administrador)],
)


@router.post("", response_model=UsuarioResposta, status_code=status.HTTP_201_CREATED)
def criar_usuario(dados: UsuarioCriar, db: Session = Depends(get_db)):
    if buscar_usuario_por_login(db, dados.usuario):
        raise RegraNegocioError("Já existe um usuário com esse login.")

    novo_usuario = Usuario(
        usuario=dados.usuario,
        nome=dados.nome,
        senha_hash=gerar_hash_senha(dados.senha),
        perfil=dados.perfil.value,
        ativo=True,
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    return novo_usuario


@router.get("", response_model=list[UsuarioResposta])
def listar_usuarios(db: Session = Depends(get_db)):
    return db.query(Usuario).order_by(Usuario.id).all()


@router.get("/{usuario_id}", response_model=UsuarioResposta)
def consultar_usuario(usuario_id: int, db: Session = Depends(get_db)):
    return usuario_ou_404(db, usuario_id)


@router.patch("/{usuario_id}/perfil", response_model=UsuarioResposta)
def alterar_perfil_usuario(
    usuario_id: int,
    dados: UsuarioPerfilAtualizar,
    db: Session = Depends(get_db),
    administrador: Usuario = Depends(exigir_administrador),
):
    usuario = usuario_ou_404(db, usuario_id)
    if usuario.id == administrador.id and dados.perfil != PerfilUsuario.ADMINISTRADOR:
        raise RegraNegocioError("O Administrador não pode remover o próprio perfil de Administrador.")
    usuario.perfil = dados.perfil.value
    db.commit()
    db.refresh(usuario)
    return usuario


@router.patch("/{usuario_id}/status", response_model=UsuarioResposta)
def alterar_status_usuario(
    usuario_id: int,
    dados: UsuarioStatusAtualizar,
    db: Session = Depends(get_db),
    administrador: Usuario = Depends(exigir_administrador),
):
    usuario = usuario_ou_404(db, usuario_id)
    if usuario.id == administrador.id and not dados.ativo:
        raise RegraNegocioError("O Administrador não pode desativar a própria conta.")
    usuario.ativo = dados.ativo
    db.commit()
    db.refresh(usuario)
    return usuario


@router.patch("/{usuario_id}/senha", response_model=MensagemResposta)
def alterar_senha_usuario(
    usuario_id: int,
    dados: UsuarioSenhaAtualizar,
    db: Session = Depends(get_db),
):
    usuario = usuario_ou_404(db, usuario_id)
    usuario.senha_hash = gerar_hash_senha(dados.nova_senha)
    db.commit()
    return MensagemResposta(mensagem=f"Senha do usuário '{usuario.usuario}' alterada com sucesso.")
