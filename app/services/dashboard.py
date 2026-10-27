from datetime import date, timedelta

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.enums.status import StatusCarga, StatusPedido
from app.models.carga import Carga
from app.models.pedido import Pedido
from app.schemas.dashboard import (
    CargasPorTransportadora,
    DashboardResumo,
    PedidosPorCidade,
    PedidosPorDia,
    ResumoCargas,
    ResumoOperacao,
    ResumoPedidos,
)


def arredondar(valor) -> float:
    return round(float(valor or 0), 2)


def contar_por_status(db: Session, coluna_status) -> dict[str, int]:
    """Uma única consulta com GROUP BY em vez de um COUNT por status."""
    return dict(db.query(coluna_status, func.count()).group_by(coluna_status).all())


def gerar_resumo_dashboard(db: Session) -> DashboardResumo:
    pedidos = contar_por_status(db, Pedido.status)
    cargas = contar_por_status(db, Carga.status)
    sem_carga, peso_total, peso_vinculado, valor_total = db.query(
        func.sum(case((Pedido.carga_id.is_(None), 1), else_=0)),
        func.sum(Pedido.peso),
        func.sum(case((Pedido.carga_id.is_not(None), Pedido.peso), else_=0)),
        func.sum(Pedido.valor_total),
    ).one()

    return DashboardResumo(
        pedidos=ResumoPedidos(
            total=sum(pedidos.values()),
            pendentes=pedidos.get(StatusPedido.PENDENTE.value, 0),
            em_separacao=pedidos.get(StatusPedido.EM_SEPARACAO.value, 0),
            carregados=pedidos.get(StatusPedido.CARREGADO.value, 0),
            em_transporte=pedidos.get(StatusPedido.EM_TRANSPORTE.value, 0),
            entregues=pedidos.get(StatusPedido.ENTREGUE.value, 0),
            cancelados=pedidos.get(StatusPedido.CANCELADO.value, 0),
            sem_carga=int(sem_carga or 0),
        ),
        cargas=ResumoCargas(
            total=sum(cargas.values()),
            planejadas=cargas.get(StatusCarga.PLANEJADA.value, 0),
            em_carregamento=cargas.get(StatusCarga.EM_CARREGAMENTO.value, 0),
            carregadas=cargas.get(StatusCarga.CARREGADA.value, 0),
            em_transporte=cargas.get(StatusCarga.EM_TRANSPORTE.value, 0),
            finalizadas=cargas.get(StatusCarga.FINALIZADA.value, 0),
            canceladas=cargas.get(StatusCarga.CANCELADA.value, 0),
        ),
        operacao=ResumoOperacao(
            peso_total_pedidos=arredondar(peso_total),
            peso_vinculado_cargas=arredondar(peso_vinculado),
            valor_total_pedidos=arredondar(valor_total),
        ),
    )


def gerar_pedidos_por_cidade(db: Session, limite: int) -> list[PedidosPorCidade]:
    quantidade = func.count(Pedido.id)
    resultados = (
        db.query(
            Pedido.cidade,
            Pedido.uf,
            quantidade.label("quantidade"),
            func.sum(Pedido.peso).label("peso_total"),
            func.sum(Pedido.valor_total).label("valor_total"),
        )
        .group_by(Pedido.cidade, Pedido.uf)
        .order_by(quantidade.desc(), Pedido.cidade, Pedido.uf)
        .limit(limite)
        .all()
    )
    return [
        PedidosPorCidade(
            cidade=linha.cidade,
            uf=linha.uf,
            quantidade=linha.quantidade,
            peso_total=arredondar(linha.peso_total),
            valor_total=arredondar(linha.valor_total),
        )
        for linha in resultados
    ]


def gerar_cargas_por_transportadora(db: Session, limite: int) -> list[CargasPorTransportadora]:
    quantidade_cargas = func.count(func.distinct(Carga.id))
    resultados = (
        db.query(
            Carga.transportadora,
            quantidade_cargas.label("quantidade_cargas"),
            func.count(Pedido.id).label("quantidade_pedidos"),
            func.sum(Pedido.peso).label("peso_total"),
        )
        .outerjoin(Pedido, Pedido.carga_id == Carga.id)
        .group_by(Carga.transportadora)
        .order_by(quantidade_cargas.desc(), Carga.transportadora)
        .limit(limite)
        .all()
    )
    return [
        CargasPorTransportadora(
            transportadora=linha.transportadora,
            quantidade_cargas=linha.quantidade_cargas,
            quantidade_pedidos=linha.quantidade_pedidos,
            peso_total=arredondar(linha.peso_total),
        )
        for linha in resultados
    ]


def gerar_pedidos_por_dia(db: Session, dias: int) -> list[PedidosPorDia]:
    inicio = date.today() - timedelta(days=dias - 1)
    dia = func.date(Pedido.criado_em)
    resultados = (
        db.query(dia.label("data"), func.count(Pedido.id).label("quantidade"))
        .filter(dia >= inicio.isoformat())
        .group_by(dia)
        .all()
    )
    quantidade_por_dia = {str(linha.data): linha.quantidade for linha in resultados}

    datas = [inicio + timedelta(days=i) for i in range(dias)]
    return [PedidosPorDia(data=data, quantidade=quantidade_por_dia.get(data.isoformat(), 0)) for data in datas]
