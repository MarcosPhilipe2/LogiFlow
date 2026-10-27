from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.dashboard import CargasPorTransportadora, DashboardResumo, PedidosPorCidade, PedidosPorDia
from app.services.dashboard import gerar_cargas_por_transportadora, gerar_pedidos_por_cidade, gerar_pedidos_por_dia, gerar_resumo_dashboard

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/resumo", response_model=DashboardResumo)
def obter_resumo_dashboard(db: Session = Depends(get_db)):
    return gerar_resumo_dashboard(db)


@router.get("/pedidos-por-cidade", response_model=list[PedidosPorCidade])
def pedidos_por_cidade(
    limite: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return gerar_pedidos_por_cidade(db, limite)


@router.get("/cargas-por-transportadora", response_model=list[CargasPorTransportadora])
def cargas_por_transportadora(
    limite: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return gerar_cargas_por_transportadora(db, limite)


@router.get("/pedidos-por-dia", response_model=list[PedidosPorDia])
def pedidos_por_dia(
    dias: int = Query(default=7, ge=1, le=365),
    db: Session = Depends(get_db),
):
    return gerar_pedidos_por_dia(db, dias)
