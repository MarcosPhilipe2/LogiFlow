from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums.historico import OrigemStatus, TipoEntidade
from app.enums.status import StatusCarga
from app.models.carga import Carga
from app.routes.comum import Paginacao, carga_ou_404, pedido_ou_404
from app.schemas.carga import CargaAtualizar, CargaCriar, CargaResposta
from app.schemas.historico import HistoricoStatusResposta
from app.schemas.pedido import PedidoResposta
from app.services.auditoria import buscar_historico, registrar_historico_carga
from app.services.cargas import garantir_numero_carga_disponivel
from app.services.erros import RegraNegocioError
from app.services.logistica import alterar_status_carga, desvincular_pedido, vincular_pedido
from app.services.permissoes import exigir_administrador, exigir_operacao

router = APIRouter(prefix="/cargas", tags=["Cargas"])


@router.post(
    "",
    response_model=CargaResposta,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(exigir_operacao)],
)
def criar_carga(dados: CargaCriar, db: Session = Depends(get_db)):
    garantir_numero_carga_disponivel(db, dados.numero_carga)
    nova = Carga(
        numero_carga=dados.numero_carga,
        transportadora=dados.transportadora,
        veiculo=dados.veiculo,
        motorista=dados.motorista,
        status=StatusCarga.PLANEJADA.value,
        data_saida=dados.data_saida,
    )
    db.add(nova)
    db.flush()
    registrar_historico_carga(db, nova, None, OrigemStatus.CRIACAO)
    db.commit()
    db.refresh(nova)
    return nova


@router.get("", response_model=list[CargaResposta])
def listar_cargas(
    response: Response,
    status_carga: StatusCarga | None = Query(default=None, alias="status"),
    paginacao: Paginacao = Depends(),
    db: Session = Depends(get_db),
):
    consulta = db.query(Carga)
    if status_carga is not None:
        consulta = consulta.filter(Carga.status == status_carga.value)
    return paginacao.aplicar(consulta.order_by(Carga.id.desc()), response)


@router.get("/{carga_id}/historico", response_model=list[HistoricoStatusResposta])
def historico_carga(carga_id: int, db: Session = Depends(get_db)):
    carga = carga_ou_404(db, carga_id)
    return buscar_historico(db, TipoEntidade.CARGA, carga.id)


@router.get("/{carga_id}/pedidos", response_model=list[PedidoResposta])
def listar_pedidos_da_carga(carga_id: int, db: Session = Depends(get_db)):
    return carga_ou_404(db, carga_id).pedidos


@router.post(
    "/{carga_id}/pedidos/{pedido_id}",
    response_model=CargaResposta,
    dependencies=[Depends(exigir_operacao)],
)
def vincular_pedido_a_carga(carga_id: int, pedido_id: int, db: Session = Depends(get_db)):
    carga = carga_ou_404(db, carga_id)
    pedido = pedido_ou_404(db, pedido_id)
    vincular_pedido(db, carga, pedido)
    db.commit()
    db.refresh(carga)
    return carga


@router.delete("/{carga_id}/pedidos/{pedido_id}", dependencies=[Depends(exigir_operacao)])
def desvincular_pedido_da_carga(carga_id: int, pedido_id: int, db: Session = Depends(get_db)):
    carga = carga_ou_404(db, carga_id)
    pedido = pedido_ou_404(db, pedido_id)
    desvincular_pedido(db, carga, pedido)
    db.commit()
    return {"mensagem": "Pedido desvinculado da carga com sucesso."}


@router.get("/{carga_id}", response_model=CargaResposta)
def buscar_carga(carga_id: int, db: Session = Depends(get_db)):
    return carga_ou_404(db, carga_id)


@router.put("/{carga_id}", response_model=CargaResposta, dependencies=[Depends(exigir_operacao)])
def atualizar_carga(carga_id: int, dados: CargaAtualizar, db: Session = Depends(get_db)):
    carga = carga_ou_404(db, carga_id)
    atualizacoes = dados.model_dump(exclude_unset=True, exclude={"status"})
    if "numero_carga" in atualizacoes:
        garantir_numero_carga_disponivel(db, atualizacoes["numero_carga"], ignorar_id=carga.id)

    for campo, valor in atualizacoes.items():
        setattr(carga, campo, valor)
    if dados.status is not None:
        alterar_status_carga(db, carga, dados.status)

    db.commit()
    db.refresh(carga)
    return carga


@router.delete("/{carga_id}", dependencies=[Depends(exigir_administrador)])
def excluir_carga(carga_id: int, db: Session = Depends(get_db)):
    carga = carga_ou_404(db, carga_id)
    if carga.pedidos:
        raise RegraNegocioError("Remova os pedidos da carga antes de excluí-la.")
    db.delete(carga)
    db.commit()
    return {"mensagem": "Carga excluída com sucesso."}
