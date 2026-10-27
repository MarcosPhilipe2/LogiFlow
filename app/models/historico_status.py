from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class HistoricoStatus(Base):
    __tablename__ = "historico_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tipo_entidade: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    entidade_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    identificador: Mapped[str] = mapped_column(String(100), nullable=False)
    status_anterior: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status_novo: Mapped[str] = mapped_column(String(30), nullable=False)
    origem: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
