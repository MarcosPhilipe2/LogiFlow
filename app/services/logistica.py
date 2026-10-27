from sqlalchemy.orm import Session

from app.enums.historico import OrigemStatus
from app.enums.status import StatusCarga, StatusPedido
from app.models.carga import Carga
from app.models.pedido import Pedido
from app.services.auditoria import registrar_historico_carga
from app.services.erros import RegraNegocioError
from app.services.pedidos import alterar_status_pedido
from app.services.status import validar_transicao_carga, validar_transicao_pedido

STATUS_PEDIDO_BLOQUEADOS_VINCULO = {
    StatusPedido.EM_TRANSPORTE.value,
    StatusPedido.ENTREGUE.value,
    StatusPedido.CANCELADO.value,
}

# Esses status só podem ser alcançados pela sincronização com a carga, nunca manualmente.
STATUS_PEDIDO_DEFINIDOS_PELA_CARGA = {
    StatusPedido.CARREGADO,
    StatusPedido.EM_TRANSPORTE,
    StatusPedido.ENTREGUE,
}

# Ao sair da carga, o pedido que ainda não tinha partido volta para Pendente.
STATUS_PEDIDO_VOLTAM_A_PENDENTE = {
    StatusPedido.EM_SEPARACAO.value,
    StatusPedido.CARREGADO.value,
}

STATUS_CARGA_PERMITIDOS_VINCULO = {
    StatusCarga.PLANEJADA.value,
    StatusCarga.EM_CARREGAMENTO.value,
}

STATUS_CARGA_BLOQUEADOS_DESVINCULO = {
    StatusCarga.EM_TRANSPORTE.value,
    StatusCarga.FINALIZADA.value,
}

STATUS_CARGA_EXIGEM_PEDIDOS = {
    StatusCarga.EM_TRANSPORTE,
    StatusCarga.FINALIZADA,
}

# Quando a carga entra no status da chave, os pedidos dela que estão no
# primeiro status da tupla avançam para o segundo.
SINCRONIZACAO_PEDIDOS = {
    StatusCarga.EM_CARREGAMENTO: (StatusPedido.PENDENTE, StatusPedido.EM_SEPARACAO),
    StatusCarga.CARREGADA: (StatusPedido.EM_SEPARACAO, StatusPedido.CARREGADO),
    StatusCarga.EM_TRANSPORTE: (StatusPedido.CARREGADO, StatusPedido.EM_TRANSPORTE),
    StatusCarga.FINALIZADA: (StatusPedido.EM_TRANSPORTE, StatusPedido.ENTREGUE),
}


def alterar_status_pedido_manual(db: Session, pedido: Pedido, novo_status: StatusPedido) -> None:
    validar_transicao_pedido(pedido.status, novo_status)
    if pedido.status == novo_status.value:
        return
    if novo_status in STATUS_PEDIDO_DEFINIDOS_PELA_CARGA:
        raise RegraNegocioError(
            f"O status '{novo_status.value}' é definido automaticamente pela carga do pedido."
        )
    if pedido.carga_id is not None and novo_status != StatusPedido.CANCELADO:
        raise RegraNegocioError(
            "Pedidos vinculados a uma carga só podem ser cancelados manualmente; "
            "os demais status acompanham a carga."
        )

    alterar_status_pedido(db, pedido, novo_status, OrigemStatus.MANUAL)
    if novo_status == StatusPedido.CANCELADO:
        # Pedido cancelado não ocupa mais espaço (nem peso) na carga.
        pedido.carga_id = None


def vincular_pedido(db: Session, carga: Carga, pedido: Pedido) -> None:
    if carga.status not in STATUS_CARGA_PERMITIDOS_VINCULO:
        raise RegraNegocioError(
            "Só é possível adicionar pedidos a cargas com status "
            "'Planejada' ou 'Em carregamento'."
        )
    if pedido.status in STATUS_PEDIDO_BLOQUEADOS_VINCULO:
        raise RegraNegocioError("O status atual do pedido não permite vínculo com uma carga.")
    if pedido.carga_id is not None and pedido.carga_id != carga.id:
        raise RegraNegocioError("O pedido já está vinculado a outra carga.")

    pedido.carga_id = carga.id
    if carga.status == StatusCarga.EM_CARREGAMENTO.value and pedido.status == StatusPedido.PENDENTE.value:
        alterar_status_pedido(db, pedido, StatusPedido.EM_SEPARACAO, OrigemStatus.VINCULO_CARGA)


def liberar_pedido(db: Session, pedido: Pedido, origem: OrigemStatus) -> None:
    if pedido.status in STATUS_PEDIDO_VOLTAM_A_PENDENTE:
        alterar_status_pedido(db, pedido, StatusPedido.PENDENTE, origem)
    pedido.carga_id = None


def desvincular_pedido(db: Session, carga: Carga, pedido: Pedido) -> None:
    if pedido.carga_id != carga.id:
        raise RegraNegocioError("O pedido não pertence a esta carga.")
    if carga.status in STATUS_CARGA_BLOQUEADOS_DESVINCULO:
        raise RegraNegocioError("Não é possível remover pedidos de uma carga em transporte ou finalizada.")
    liberar_pedido(db, pedido, OrigemStatus.DESVINCULO_CARGA)


def alterar_status_carga(db: Session, carga: Carga, novo_status: StatusCarga) -> None:
    validar_transicao_carga(carga.status, novo_status)
    if carga.status == novo_status.value:
        return
    if novo_status in STATUS_CARGA_EXIGEM_PEDIDOS and not carga.pedidos:
        raise RegraNegocioError("A carga precisa possuir pelo menos um pedido antes de avançar para esse status.")

    status_anterior = carga.status
    carga.status = novo_status.value
    registrar_historico_carga(db, carga, status_anterior, OrigemStatus.MANUAL)

    if novo_status == StatusCarga.CANCELADA:
        for pedido in list(carga.pedidos):
            liberar_pedido(db, pedido, OrigemStatus.CANCELAMENTO_CARGA)
    else:
        sincronizar_pedidos_com_carga(db, carga, novo_status)


def sincronizar_pedidos_com_carga(db: Session, carga: Carga, novo_status: StatusCarga) -> None:
    regra = SINCRONIZACAO_PEDIDOS.get(novo_status)
    if regra is None:
        return
    status_origem, status_destino = regra
    for pedido in carga.pedidos:
        if pedido.status == status_origem.value:
            alterar_status_pedido(db, pedido, status_destino, OrigemStatus.SINCRONIZACAO_CARGA)
