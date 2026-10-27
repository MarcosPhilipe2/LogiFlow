from datetime import date

from pydantic import BaseModel


class ResumoPedidos(BaseModel):
    total: int
    pendentes: int
    em_separacao: int
    carregados: int
    em_transporte: int
    entregues: int
    cancelados: int
    sem_carga: int


class ResumoCargas(BaseModel):
    total: int
    planejadas: int
    em_carregamento: int
    carregadas: int
    em_transporte: int
    finalizadas: int
    canceladas: int


class ResumoOperacao(BaseModel):
    peso_total_pedidos: float
    peso_vinculado_cargas: float
    valor_total_pedidos: float


class DashboardResumo(BaseModel):
    pedidos: ResumoPedidos
    cargas: ResumoCargas
    operacao: ResumoOperacao


class PedidosPorCidade(BaseModel):
    cidade: str
    uf: str
    quantidade: int
    peso_total: float
    valor_total: float


class CargasPorTransportadora(BaseModel):
    transportadora: str
    quantidade_cargas: int
    quantidade_pedidos: int
    peso_total: float


class PedidosPorDia(BaseModel):
    data: date
    quantidade: int
