"""Verifica a API e a conexão com o banco sem dependências adicionais."""
import os
from urllib.request import urlopen

with urlopen(f"http://127.0.0.1:{os.getenv('PORT', '8000')}/database/status", timeout=4) as resposta:
    if resposta.status != 200:
        raise SystemExit(1)
