from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.pedido import Pedido


class Carga(Base):
    __tablename__ = "cargas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    numero_carga: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    transportadora: Mapped[str] = mapped_column(String(150), nullable=False)
    veiculo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    motorista: Mapped[str | None] = mapped_column(String(150), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="Planejada")
    data_saida: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    pedidos: Mapped[list["Pedido"]] = relationship(
        back_populates="carga",
        lazy="selectin",
        order_by="Pedido.id",
    )

    @property
    def peso_total(self) -> float:
        return round(sum(pedido.peso for pedido in self.pedidos), 2)
