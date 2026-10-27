import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET_KEY
from app.database import get_db
from app.models.usuario import Usuario

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Usado quando o login não existe, para que a resposta leve o mesmo tempo
# de um login existente com senha errada (evita descobrir usuários pelo tempo).
_HASH_FICTICIO = password_hash.hash("senha-ficticia-para-equalizar-o-tempo")


def normalizar_usuario(usuario: str) -> str:
    return usuario.strip().lower()


def gerar_hash_senha(senha: str) -> str:
    return password_hash.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return password_hash.verify(senha, senha_hash)


def buscar_usuario_por_login(db: Session, usuario: str) -> Usuario | None:
    login = normalizar_usuario(usuario)
    return db.query(Usuario).filter(Usuario.usuario == login).first()


def autenticar_usuario(db: Session, usuario: str, senha: str) -> Usuario | None:
    usuario_db = buscar_usuario_por_login(db, usuario)
    if usuario_db is None:
        verificar_senha(senha, _HASH_FICTICIO)
        return None
    if not verificar_senha(senha, usuario_db.senha_hash) or not usuario_db.ativo:
        return None
    return usuario_db


def versao_da_senha(usuario: Usuario) -> str:
    """Muda sempre que a senha muda; tokens emitidos antes da troca deixam de valer."""
    return hmac.new(JWT_SECRET_KEY.encode(), usuario.senha_hash.encode(), hashlib.sha256).hexdigest()[:16]


def criar_token_acesso(usuario: Usuario) -> str:
    agora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario.id),
        "usuario": usuario.usuario,
        "perfil": usuario.perfil,
        "sv": versao_da_senha(usuario),
        "iat": agora,
        "exp": agora + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def obter_usuario_atual(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    erro = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        usuario_id = int(payload["sub"])
        versao_token = str(payload["sv"])
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        raise erro

    usuario = db.get(Usuario, usuario_id)
    if not usuario or not hmac.compare_digest(versao_token, versao_da_senha(usuario)):
        raise erro
    if not usuario.ativo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário desativado.")
    return usuario
