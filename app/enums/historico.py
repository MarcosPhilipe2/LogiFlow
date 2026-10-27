from enum import Enum


class TipoEntidade(str, Enum):
    PEDIDO = "pedido"
    CARGA = "carga"


class OrigemStatus(str, Enum):
    CRIACAO = "criacao"
    MANUAL = "manual"
    VINCULO_CARGA = "vinculo_carga"
    DESVINCULO_CARGA = "desvinculo_carga"
    SINCRONIZACAO_CARGA = "sincronizacao_carga"
    CANCELAMENTO_CARGA = "cancelamento_carga"
