"""Carrega pedidos e cargas de demonstração em um banco vazio.

Usa as mesmas regras da API (vínculo, sincronização de status e histórico),
então os dados ficam coerentes com o que a API produziria.

    python -m scripts.popular_demo
"""
import random
from datetime import datetime, timedelta
from itertools import count

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.enums.historico import OrigemStatus
from app.enums.status import StatusCarga, StatusPedido
from app.models.carga import Carga
from app.models.pedido import Pedido
from app.services.auditoria import registrar_historico_carga, registrar_historico_pedido
from app.services.logistica import alterar_status_carga, alterar_status_pedido_manual, vincular_pedido

CLIENTES = [
    "Mercado Bom Preço", "Farmácia Vida", "Construtora Alicerce", "Loja do Lar",
    "Distribuidora Central", "Padaria Pão Nosso", "AutoPeças Silva", "Papelaria Escolar",
    "Hospital Santa Clara", "Restaurante Sabor Caseiro",
]
CIDADES = [
    ("São Paulo", "SP"), ("Campinas", "SP"), ("Rio de Janeiro", "RJ"), ("Belo Horizonte", "MG"),
    ("Curitiba", "PR"), ("Porto Alegre", "RS"), ("Salvador", "BA"), ("Recife", "PE"),
]
TRANSPORTADORAS = ["Rápido Sul", "TransBrasil Cargas", "Expresso Minas", "Log Norte"]
MOTORISTAS = ["Carlos Souza", "Ana Lima", "João Pereira", "Marcos Rocha", "Fernanda Alves"]

FLUXO_CARGA = [StatusCarga.EM_CARREGAMENTO, StatusCarga.CARREGADA, StatusCarga.EM_TRANSPORTE, StatusCarga.FINALIZADA]

# (status final da carga, quantidade de pedidos)
CARGAS_DEMO = [
    (StatusCarga.FINALIZADA, 4),
    (StatusCarga.FINALIZADA, 3),
    (StatusCarga.EM_TRANSPORTE, 4),
    (StatusCarga.CARREGADA, 3),
    (StatusCarga.EM_CARREGAMENTO, 3),
    (StatusCarga.PLANEJADA, 2),
    (StatusCarga.CANCELADA, 2),
]

# Pedidos que ficam fora de qualquer carga, por status.
PEDIDOS_AVULSOS = {
    StatusPedido.PENDENTE: 5,
    StatusPedido.EM_SEPARACAO: 2,
    StatusPedido.CANCELADO: 2,
}


def popular(db: Session) -> None:
    aleatorio = random.Random(2026)
    agora = datetime.now()
    numeros_pedido = count(1)

    def novo_pedido() -> Pedido:
        cidade, uf = aleatorio.choice(CIDADES)
        pedido = Pedido(
            numero_pedido=f"PED-{next(numeros_pedido):04d}",
            cliente=aleatorio.choice(CLIENTES),
            cidade=cidade,
            uf=uf,
            status=StatusPedido.PENDENTE.value,
            peso=round(aleatorio.uniform(50, 1500), 1),
            valor_total=round(aleatorio.uniform(500, 25000), 2),
            criado_em=agora - timedelta(days=aleatorio.randint(0, 13), hours=aleatorio.randint(0, 9)),
        )
        db.add(pedido)
        db.flush()
        registrar_historico_pedido(db, pedido, None, OrigemStatus.CRIACAO)
        return pedido

    for indice, (status_final, quantidade) in enumerate(CARGAS_DEMO, start=1):
        carga = Carga(
            numero_carga=f"CAR-{indice:03d}",
            transportadora=aleatorio.choice(TRANSPORTADORAS),
            veiculo=f"{aleatorio.choice('ABCDEFGHJ')}{aleatorio.choice('ABCDEFGHJ')}C{aleatorio.randint(1, 9)}D{aleatorio.randint(10, 99)}",
            motorista=aleatorio.choice(MOTORISTAS),
            status=StatusCarga.PLANEJADA.value,
            data_saida=agora - timedelta(days=aleatorio.randint(0, 5)) if status_final in FLUXO_CARGA[2:] else None,
        )
        db.add(carga)
        db.flush()
        registrar_historico_carga(db, carga, None, OrigemStatus.CRIACAO)
        for _ in range(quantidade):
            vincular_pedido(db, carga, novo_pedido())
        db.commit()

        if status_final == StatusCarga.CANCELADA:
            caminho = [StatusCarga.EM_CARREGAMENTO, StatusCarga.CANCELADA]
        elif status_final == StatusCarga.PLANEJADA:
            caminho = []
        else:
            caminho = FLUXO_CARGA[: FLUXO_CARGA.index(status_final) + 1]
        for proximo_status in caminho:
            alterar_status_carga(db, carga, proximo_status)
            db.commit()

    for status_final, quantidade in PEDIDOS_AVULSOS.items():
        for _ in range(quantidade):
            pedido = novo_pedido()
            if status_final != StatusPedido.PENDENTE:
                alterar_status_pedido_manual(db, pedido, status_final)
    db.commit()


def main() -> None:
    with SessionLocal() as db:
        if db.query(Pedido).count() > 0:
            print("O banco já possui pedidos; os dados de demonstração não foram carregados.")
            return
        popular(db)
        total_pedidos = db.query(Pedido).count()
        total_cargas = db.query(Carga).count()
    print(f"Dados de demonstração carregados: {total_pedidos} pedidos e {total_cargas} cargas.")


if __name__ == "__main__":
    main()
