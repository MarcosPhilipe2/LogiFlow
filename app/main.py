import logging
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from fastapi import Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app import config
from app.config import VERSAO_API
from app.database import get_db
from app.protecao import ProtecaoContraSobrecarga
from app.routes.auth import router as auth_router
from app.routes.cargas import router as cargas_router
from app.routes.dashboard import router as dashboard_router
from app.routes.pedidos import router as pedidos_router
from app.routes.usuarios import router as usuarios_router
from app.services.auth import obter_usuario_atual
from app.services.erros import RegraNegocioError

logger = logging.getLogger(__name__)

app = FastAPI(
    title="LogiFlow API",
    description="API para gerenciamento de pedidos, cargas e operações logísticas.",
    version=VERSAO_API,
)

if config.LIMITE_ATIVO:
    app.add_middleware(
        ProtecaoContraSobrecarga,
        max_simultaneas=config.LIMITE_SIMULTANEAS,
        por_minuto=config.LIMITE_POR_MINUTO,
        rajada=config.LIMITE_RAJADA,
        login_por_minuto=config.LIMITE_LOGIN_POR_MINUTO,
        login_rajada=config.LIMITE_LOGIN_RAJADA,
        max_logins_simultaneos=config.LIMITE_LOGINS_SIMULTANEOS,
        max_escritas_na_fila=config.LIMITE_ESCRITAS_NA_FILA,
    )

# Qualquer usuário autenticado pode ler; as rotas de escrita declaram o perfil exigido.
app.include_router(auth_router)
app.include_router(usuarios_router)
app.include_router(pedidos_router, dependencies=[Depends(obter_usuario_atual)])
app.include_router(cargas_router, dependencies=[Depends(obter_usuario_atual)])
app.include_router(dashboard_router, dependencies=[Depends(obter_usuario_atual)])


@app.exception_handler(RegraNegocioError)
async def responder_regra_de_negocio(request: Request, erro: RegraNegocioError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(erro)})


@app.exception_handler(IntegrityError)
async def responder_violacao_de_integridade(request: Request, erro: IntegrityError) -> JSONResponse:
    # Rede de segurança: as rotas já checam duplicidade antes; isto cobre corridas entre requisições.
    logger.warning("Violação de integridade no banco: %s", erro.orig)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "A operação conflita com dados já cadastrados."},
    )


@app.get("/", tags=["Sistema"])
def inicio():
    return {"mensagem": "LogiFlow API está funcionando.", "versao": VERSAO_API}


@app.get("/status", tags=["Sistema"])
def verificar_status():
    return {"status": "online"}


@app.get("/database/status", tags=["Sistema"])
def verificar_banco(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("Falha ao conectar ao banco de dados.")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "erro", "mensagem": "Não foi possível conectar ao banco."},
        )
    return {
        "status": "conectado",
        "banco": db.get_bind().dialect.name,
        "mensagem": "Conexão com o banco realizada com sucesso.",
    }


# Interface servida pela mesma origem da API, inclusive em outros computadores.
PASTA_INTERFACE = Path(__file__).resolve().parent / "static"
app.mount("/interface/arquivos", StaticFiles(directory=PASTA_INTERFACE), name="interface-arquivos")


@app.get("/interface", include_in_schema=False)
@app.get("/interface/", include_in_schema=False)
def interface():
    return FileResponse(PASTA_INTERFACE / "index.html", headers={"Cache-Control": "no-store"})
