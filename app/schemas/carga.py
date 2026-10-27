from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.enums.status import StatusCarga
from app.schemas.comum import Codigo, rejeitar_nulo


class CargaCriar(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    numero_carga: Codigo
    transportadora: str = Field(min_length=2, max_length=150)
    veiculo: str | None = Field(default=None, max_length=50)
    motorista: str | None = Field(default=None, max_length=150)
    status: Literal[StatusCarga.PLANEJADA] = Field(
        default=StatusCarga.PLANEJADA,
        description="Toda carga começa Planejada; depois o status avança pelas transições permitidas.",
    )
    data_saida: datetime | None = None


class CargaAtualizar(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    numero_carga: Codigo | None = None
    transportadora: str | None = Field(default=None, min_length=2, max_length=150)
    veiculo: str | None = Field(default=None, max_length=50)
    motorista: str | None = Field(default=None, max_length=150)
    status: StatusCarga | None = None
    data_saida: datetime | None = None

    validar_campos_obrigatorios = field_validator(
        "numero_carga", "transportadora", "status", mode="before",
    )(rejeitar_nulo)


class CargaResposta(BaseModel):
    id: int
    numero_carga: str
    transportadora: str
    veiculo: str | None
    motorista: str | None
    status: StatusCarga
    data_saida: datetime | None
    peso_total: float
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)
