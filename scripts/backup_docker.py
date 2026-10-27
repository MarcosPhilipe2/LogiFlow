"""Backup consistente de SQLite pelo recurso nativo, incluindo dados em WAL."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def fazer_backup(origem: Path, destino: Path) -> None:
    if not origem.is_file():
        raise FileNotFoundError(f'Banco não encontrado: {origem}')
    if destino.exists():
        raise FileExistsError(f'O destino já existe: {destino}')
    destino.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(origem.resolve().as_uri() + '?mode=ro', uri=True) as banco:
        with sqlite3.connect(destino) as copia:
            banco.backup(copia)
            if copia.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RuntimeError('Falha na verificação de integridade do backup.')


def main() -> None:
    destino = Path('/dados/backups') / ('logiflow-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f') + '.db')
    fazer_backup(Path('/dados/logiflow.db'), destino)
    print(f'Backup criado: {destino}')


if __name__ == '__main__':
    main()
