from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL

USANDO_SQLITE = DATABASE_URL.startswith("sqlite")

if USANDO_SQLITE:
    # O pool padrão (5 + 10 conexões, espera de 30 s) travava a API inteira sob carga: as threads
    # das rotas ficavam esperando conexão enquanto quem as segurava esperava uma thread livre para
    # devolvê-las. Conexões SQLite são baratas, então o pool cria extras em vez de fazer esperar.
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_size=20,
        max_overflow=-1,
    )
else:
    engine = create_engine(
        DATABASE_URL, pool_pre_ping=True, pool_size=3, max_overflow=2,
        pool_timeout=15, pool_recycle=300, connect_args={"connect_timeout": 10},
    )

if USANDO_SQLITE:
    @event.listens_for(engine, "connect")
    def configurar_sqlite(conexao, _registro):
        cursor = conexao.cursor()
        # O SQLite ignora FOREIGN KEY a menos que isso seja ligado em cada conexão.
        cursor.execute("PRAGMA foreign_keys=ON")
        # WAL: leituras não esperam a gravação terminar (e vice-versa).
        cursor.execute("PRAGMA journal_mode=WAL")
        # Com várias gravações ao mesmo tempo, espera a vez em vez de falhar com "database is locked".
        cursor.execute("PRAGMA busy_timeout=15000")
        cursor.close()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
