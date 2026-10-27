from sqlalchemy.orm import Session

from app.models.carga import Carga
from app.services.erros import RegraNegocioError


def normalizar_numero_carga(numero_carga: str) -> str:
    return numero_carga.strip().upper()


def buscar_carga_por_numero(db: Session, numero_carga: str) -> Carga | None:
    numero_normalizado = normalizar_numero_carga(numero_carga)
    return db.query(Carga).filter(Carga.numero_carga == numero_normalizado).first()


def garantir_numero_carga_disponivel(db: Session, numero_carga: str, ignorar_id: int | None = None) -> None:
    existente = buscar_carga_por_numero(db, numero_carga)
    if existente is not None and existente.id != ignorar_id:
        raise RegraNegocioError("Já existe uma carga com esse número.")
