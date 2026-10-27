from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.enums.status import StatusPedido
from app.schemas.comum import UF, Codigo, rejeitar_nulo


class PedidoCriar(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    numero_pedido: Codigo
    cliente: str = Field(min_length=2, max_length=150)
    cidade: str = Field(min_length=2, max_length=100)
    uf: UF
    status: Literal[StatusPedido.PENDENTE] = Field(
        default=StatusPedido.PENDENTE,
        description="Todo pedido começa Pendente; depois o status avança pelas transições permitidas.",
    )
    peso: float = Field(default=0, ge=0)
    valor_total: float = Field(default=0, ge=0)
    observacao: str | None = None


class PedidoAtualizar(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    numero_pedido: Codigo | None = None
    cliente: str | None = Field(default=None, min_length=2, max_length=150)
    cidade: str | None = Field(default=None, min_length=2, max_length=100)
    uf: UF | None = None
    status: StatusPedido | None = None
    peso: float | None = Field(default=None, ge=0)
    valor_total: float | None = Field(default=None, ge=0)
    observacao: str | None = None

    validar_campos_obrigatorios = field_validator(
        "numero_pedido", "cliente", "cidade", "uf", "status", "peso", "valor_total", mode="before",
    )(rejeitar_nulo)


class PedidoResposta(BaseModel):
    id: int
    numero_pedido: str
    cliente: str
    cidade: str
    uf: str
    status: StatusPedido
    peso: float
    valor_total: float
    observacao: str | None
    carga_id: int | None
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)
