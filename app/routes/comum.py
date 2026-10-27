from fastapi import HTTPException, Query, Response, status
from sqlalchemy.orm import Query as ConsultaSQL
from sqlalchemy.orm import Session

from app.models.carga import Carga
from app.models.pedido import Pedido
from app.models.usuario import Usuario
from app.services.pedidos import buscar_pedido_por_numero


class Paginacao:
    """Parâmetros ?offset= e ?limite= das listagens. O total sem paginação vai no cabeçalho X-Total-Count."""

    def __init__(
        self,
        offset: int = Query(default=0, ge=0, description="Quantos registros pular."),
        limite: int = Query(default=100, ge=1, le=500, description="Máximo de registros retornados."),
    ):
        self.offset = offset
        self.limite = limite

    def aplicar(self, consulta: ConsultaSQL, response: Response) -> list:
        response.headers["X-Total-Count"] = str(consulta.order_by(None).count())
        return consulta.offset(self.offset).limit(self.limite).all()


def _nao_encontrado(mensagem: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=mensagem)


def pedido_ou_404(db: Session, pedido_id: int) -> Pedido:
    pedido = db.get(Pedido, pedido_id)
    if pedido is None:
        raise _nao_encontrado("Pedido não encontrado.")
    return pedido


def pedido_por_numero_ou_404(db: Session, numero_pedido: str) -> Pedido:
    pedido = buscar_pedido_por_numero(db, numero_pedido)
    if pedido is None:
        raise _nao_encontrado("Pedido não encontrado.")
    return pedido


def carga_ou_404(db: Session, carga_id: int) -> Carga:
    carga = db.get(Carga, carga_id)
    if carga is None:
        raise _nao_encontrado("Carga não encontrada.")
    return carga


def usuario_ou_404(db: Session, usuario_id: int) -> Usuario:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise _nao_encontrado("Usuário não encontrado.")
    return usuario
