from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.carga import Carga


class Pedido(Base):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    numero_pedido: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    cliente: Mapped[str] = mapped_column(String(150), nullable=False)
    cidade: Mapped[str] = mapped_column(String(100), nullable=False)
    uf: Mapped[str] = mapped_column(String(2), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="Pendente")
    peso: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    valor_total: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    carga_id: Mapped[int | None] = mapped_column(ForeignKey("cargas.id"), nullable=True, index=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    carga: Mapped["Carga | None"] = relationship(back_populates="pedidos")
