from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums.historico import OrigemStatus, TipoEntidade
from app.enums.status import StatusPedido
from app.models.pedido import Pedido
from app.routes.comum import Paginacao, pedido_ou_404, pedido_por_numero_ou_404
from app.schemas.historico import HistoricoStatusResposta
from app.schemas.pedido import PedidoAtualizar, PedidoCriar, PedidoResposta
from app.services.auditoria import buscar_historico, registrar_historico_pedido
from app.services.erros import RegraNegocioError
from app.services.logistica import alterar_status_pedido_manual
from app.services.pedidos import garantir_numero_pedido_disponivel
from app.services.permissoes import exigir_administrador, exigir_operacao

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


def aplicar_atualizacao_pedido(db: Session, pedido: Pedido, dados: PedidoAtualizar) -> Pedido:
    atualizacoes = dados.model_dump(exclude_unset=True, exclude={"status"})
    if "numero_pedido" in atualizacoes:
        garantir_numero_pedido_disponivel(db, atualizacoes["numero_pedido"], ignorar_id=pedido.id)

    for campo, valor in atualizacoes.items():
        setattr(pedido, campo, valor)
    if dados.status is not None:
        alterar_status_pedido_manual(db, pedido, dados.status)

    db.commit()
    db.refresh(pedido)
    return pedido


@router.post(
    "",
    response_model=PedidoResposta,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(exigir_operacao)],
)
def criar_pedido(dados: PedidoCriar, db: Session = Depends(get_db)):
    garantir_numero_pedido_disponivel(db, dados.numero_pedido)
    novo = Pedido(
        numero_pedido=dados.numero_pedido,
        cliente=dados.cliente,
        cidade=dados.cidade,
        uf=dados.uf,
        status=StatusPedido.PENDENTE.value,
        peso=dados.peso,
        valor_total=dados.valor_total,
        observacao=dados.observacao,
    )
    db.add(novo)
    db.flush()
    registrar_historico_pedido(db, novo, None, OrigemStatus.CRIACAO)
    db.commit()
    db.refresh(novo)
    return novo


@router.get("", response_model=list[PedidoResposta])
def listar_pedidos(
    response: Response,
    status_pedido: StatusPedido | None = Query(default=None, alias="status"),
    sem_carga: bool | None = Query(default=None, description="true: só pedidos sem carga; false: só com carga."),
    paginacao: Paginacao = Depends(),
    db: Session = Depends(get_db),
):
    consulta = db.query(Pedido)
    if status_pedido is not None:
        consulta = consulta.filter(Pedido.status == status_pedido.value)
    if sem_carga is not None:
        consulta = consulta.filter(Pedido.carga_id.is_(None) if sem_carga else Pedido.carga_id.is_not(None))
    return paginacao.aplicar(consulta.order_by(Pedido.id.desc()), response)


@router.get("/numero/{numero_pedido}/historico", response_model=list[HistoricoStatusResposta])
def historico_por_numero(numero_pedido: str, db: Session = Depends(get_db)):
    pedido = pedido_por_numero_ou_404(db, numero_pedido)
    return buscar_historico(db, TipoEntidade.PEDIDO, pedido.id)


@router.get("/numero/{numero_pedido}", response_model=PedidoResposta)
def buscar_por_numero(numero_pedido: str, db: Session = Depends(get_db)):
    return pedido_por_numero_ou_404(db, numero_pedido)


@router.put("/numero/{numero_pedido}", response_model=PedidoResposta, dependencies=[Depends(exigir_operacao)])
def atualizar_por_numero(numero_pedido: str, dados: PedidoAtualizar, db: Session = Depends(get_db)):
    pedido = pedido_por_numero_ou_404(db, numero_pedido)
    return aplicar_atualizacao_pedido(db, pedido, dados)


@router.get("/{pedido_id}/historico", response_model=list[HistoricoStatusResposta])
def historico_por_id(pedido_id: int, db: Session = Depends(get_db)):
    pedido = pedido_ou_404(db, pedido_id)
    return buscar_historico(db, TipoEntidade.PEDIDO, pedido.id)


@router.get("/{pedido_id}", response_model=PedidoResposta)
def buscar_pedido(pedido_id: int, db: Session = Depends(get_db)):
    return pedido_ou_404(db, pedido_id)


@router.put("/{pedido_id}", response_model=PedidoResposta, dependencies=[Depends(exigir_operacao)])
def atualizar_pedido(pedido_id: int, dados: PedidoAtualizar, db: Session = Depends(get_db)):
    pedido = pedido_ou_404(db, pedido_id)
    return aplicar_atualizacao_pedido(db, pedido, dados)


@router.delete("/{pedido_id}", dependencies=[Depends(exigir_administrador)])
def excluir_pedido(pedido_id: int, db: Session = Depends(get_db)):
    pedido = pedido_ou_404(db, pedido_id)
    if pedido.carga_id is not None:
        raise RegraNegocioError("Desvincule o pedido da carga antes de excluí-lo.")
    db.delete(pedido)
    db.commit()
    return {"mensagem": "Pedido excluído com sucesso."}
