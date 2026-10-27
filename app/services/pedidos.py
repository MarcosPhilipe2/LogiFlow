from sqlalchemy.orm import Session

from app.enums.historico import OrigemStatus
from app.enums.status import StatusPedido
from app.models.pedido import Pedido
from app.services.auditoria import registrar_historico_pedido
from app.services.erros import RegraNegocioError
from app.services.status import validar_transicao_pedido


def normalizar_numero_pedido(numero_pedido: str) -> str:
    return numero_pedido.strip().upper()


def buscar_pedido_por_numero(db: Session, numero_pedido: str) -> Pedido | None:
    numero_normalizado = normalizar_numero_pedido(numero_pedido)
    return db.query(Pedido).filter(Pedido.numero_pedido == numero_normalizado).first()


def garantir_numero_pedido_disponivel(db: Session, numero_pedido: str, ignorar_id: int | None = None) -> None:
    existente = buscar_pedido_por_numero(db, numero_pedido)
    if existente is not None and existente.id != ignorar_id:
        raise RegraNegocioError("Já existe um pedido com esse número.")


def alterar_status_pedido(db: Session, pedido: Pedido, novo_status: StatusPedido, origem: OrigemStatus) -> None:
    validar_transicao_pedido(pedido.status, novo_status)
    if pedido.status == novo_status.value:
        return
    status_anterior = pedido.status
    pedido.status = novo_status.value
    registrar_historico_pedido(db, pedido, status_anterior, origem)
