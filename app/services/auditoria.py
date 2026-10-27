from sqlalchemy.orm import Session

from app.enums.historico import OrigemStatus, TipoEntidade
from app.models.carga import Carga
from app.models.historico_status import HistoricoStatus
from app.models.pedido import Pedido


def registrar_historico_status(
    db: Session,
    tipo_entidade: TipoEntidade,
    entidade_id: int,
    identificador: str,
    status_anterior: str | None,
    status_novo: str,
    origem: OrigemStatus,
) -> HistoricoStatus:
    historico = HistoricoStatus(
        tipo_entidade=tipo_entidade.value,
        entidade_id=entidade_id,
        identificador=identificador,
        status_anterior=status_anterior,
        status_novo=status_novo,
        origem=origem.value,
    )
    db.add(historico)
    return historico


def registrar_historico_pedido(
    db: Session, pedido: Pedido, status_anterior: str | None, origem: OrigemStatus,
) -> HistoricoStatus:
    return registrar_historico_status(
        db, TipoEntidade.PEDIDO, pedido.id, pedido.numero_pedido, status_anterior, pedido.status, origem,
    )


def registrar_historico_carga(
    db: Session, carga: Carga, status_anterior: str | None, origem: OrigemStatus,
) -> HistoricoStatus:
    return registrar_historico_status(
        db, TipoEntidade.CARGA, carga.id, carga.numero_carga, status_anterior, carga.status, origem,
    )


def buscar_historico(db: Session, tipo_entidade: TipoEntidade, entidade_id: int) -> list[HistoricoStatus]:
    return (
        db.query(HistoricoStatus)
        .filter(
            HistoricoStatus.tipo_entidade == tipo_entidade.value,
            HistoricoStatus.entidade_id == entidade_id,
        )
        .order_by(HistoricoStatus.criado_em.asc(), HistoricoStatus.id.asc())
        .all()
    )
