from enum import Enum

from app.enums.status import StatusCarga, StatusPedido
from app.services.erros import RegraNegocioError

# A volta para Pendente acontece quando o pedido sai da carga (desvínculo ou carga cancelada).
TRANSICOES_PEDIDO = {
    StatusPedido.PENDENTE: {StatusPedido.EM_SEPARACAO, StatusPedido.CANCELADO},
    StatusPedido.EM_SEPARACAO: {StatusPedido.PENDENTE, StatusPedido.CARREGADO, StatusPedido.CANCELADO},
    StatusPedido.CARREGADO: {StatusPedido.PENDENTE, StatusPedido.EM_TRANSPORTE, StatusPedido.CANCELADO},
    StatusPedido.EM_TRANSPORTE: {StatusPedido.ENTREGUE},
    StatusPedido.ENTREGUE: set(),
    StatusPedido.CANCELADO: set(),
}

TRANSICOES_CARGA = {
    StatusCarga.PLANEJADA: {StatusCarga.EM_CARREGAMENTO, StatusCarga.CANCELADA},
    StatusCarga.EM_CARREGAMENTO: {StatusCarga.CARREGADA, StatusCarga.CANCELADA},
    StatusCarga.CARREGADA: {StatusCarga.EM_TRANSPORTE, StatusCarga.CANCELADA},
    StatusCarga.EM_TRANSPORTE: {StatusCarga.FINALIZADA},
    StatusCarga.FINALIZADA: set(),
    StatusCarga.CANCELADA: set(),
}


def _validar_transicao(entidade: str, transicoes: dict, status_atual: str, novo_status: Enum) -> None:
    tipo_status = type(novo_status)
    try:
        atual = tipo_status(status_atual)
    except ValueError as erro:
        raise RegraNegocioError(f"{entidade.capitalize()} possui um status inválido gravado no banco.") from erro

    if atual == novo_status:
        return

    permitidos = transicoes[atual]
    if novo_status not in permitidos:
        # Percorre o Enum (e não o set) para listar as opções sempre na ordem do fluxo.
        opcoes = ", ".join(s.value for s in tipo_status if s in permitidos) or "nenhuma"
        raise RegraNegocioError(
            f"Não é permitido alterar {entidade} de '{atual.value}' "
            f"para '{novo_status.value}'. Próximos status permitidos: {opcoes}."
        )


def validar_transicao_pedido(status_atual: str, novo_status: StatusPedido) -> None:
    _validar_transicao("o pedido", TRANSICOES_PEDIDO, status_atual, novo_status)


def validar_transicao_carga(status_atual: str, novo_status: StatusCarga) -> None:
    _validar_transicao("a carga", TRANSICOES_CARGA, status_atual, novo_status)
