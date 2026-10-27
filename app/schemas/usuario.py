from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.enums.perfil_usuario import PerfilUsuario

Login = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=3, max_length=50)]


class UsuarioCriar(BaseModel):
    # Sem str_strip_whitespace no modelo: espaços na senha fazem parte dela.
    usuario: Login
    nome: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=150)]
    senha: str = Field(min_length=8, max_length=128)
    perfil: PerfilUsuario


class UsuarioPerfilAtualizar(BaseModel):
    perfil: PerfilUsuario


class UsuarioStatusAtualizar(BaseModel):
    ativo: bool


class UsuarioSenhaAtualizar(BaseModel):
    nova_senha: str = Field(min_length=8, max_length=128)


class MinhaSenhaAtualizar(BaseModel):
    senha_atual: str = Field(max_length=128)
    nova_senha: str = Field(min_length=8, max_length=128)


class UsuarioResposta(BaseModel):
    id: int
    usuario: str
    nome: str
    perfil: PerfilUsuario
    ativo: bool
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResposta(BaseModel):
    access_token: str
    token_type: str


class MensagemResposta(BaseModel):
    mensagem: str
