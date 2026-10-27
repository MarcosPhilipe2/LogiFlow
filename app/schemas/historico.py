from datetime import datetime

from pydantic import BaseModel, ConfigDict


class HistoricoStatusResposta(BaseModel):
    id: int
    tipo_entidade: str
    entidade_id: int
    identificador: str
    status_anterior: str | None
    status_novo: str
    origem: str
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)
