from enum import Enum


class StatusPedido(str, Enum):
    PENDENTE = "Pendente"
    EM_SEPARACAO = "Em separação"
    CARREGADO = "Carregado"
    EM_TRANSPORTE = "Em transporte"
    ENTREGUE = "Entregue"
    CANCELADO = "Cancelado"


class StatusCarga(str, Enum):
    PLANEJADA = "Planejada"
    EM_CARREGAMENTO = "Em carregamento"
    CARREGADA = "Carregada"
    EM_TRANSPORTE = "Em transporte"
    FINALIZADA = "Finalizada"
    CANCELADA = "Cancelada"
