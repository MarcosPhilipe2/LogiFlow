"""Proteção contra sobrecarga (rate limit).

Middleware ASGI com estas camadas, verificadas nesta ordem:

1. Limite por IP (token bucket): permite rajadas curtas; quem continua
   acima da taxa recebe 429 com o cabeçalho Retry-After.
2. Limite de login por IP, mais rígido: o hash Argon2 é caro e o login
   é o alvo de ataques de força bruta.
3. Teto de logins em andamento: o login custa ~10x uma leitura, então uma
   onda de logins vindos de vários IPs não pode tomar a CPU das demais rotas.
4. Fila de gravação: dentro de cada processo, as requisições que gravam
   (POST/PUT/PATCH/DELETE) são atendidas uma de cada vez, em ordem de
   chegada. O SQLite só grava uma coisa por vez e, quando muitas threads
   disputam o arquivo, algumas perdem a vez repetidamente até falhar com
   "database is locked". Com a fila, só um gravador por processo disputa
   o arquivo; se a fila passar do limite, responde 503.
5. Teto global de requisições em andamento: acima dele a API responde
   503 na hora, em vez de acumular uma fila que faz todas as respostas
   demorarem até estourar o tempo.

O estado fica na memória do processo, então os limites valem por processo
do uvicorn. O IP é o da conexão: atrás de um proxy reverso, todos os
usuários chegariam com o IP do proxy.
"""
import asyncio
import json
import math
import time
from collections.abc import Callable
from dataclasses import dataclass

ROTA_LOGIN = "/auth/login"
METODOS_DE_ESCRITA = frozenset({"POST", "PUT", "PATCH", "DELETE"})


@dataclass
class _Balde:
    fichas: float
    atualizado_em: float


class LimitadorPorCliente:
    """Token bucket por chave: `rajada` fichas no máximo, repostas a `por_minuto` por minuto."""

    INTERVALO_LIMPEZA = 60.0

    def __init__(self, por_minuto: int, rajada: int, relogio: Callable[[], float] = time.monotonic):
        self.taxa_por_segundo = por_minuto / 60
        self.capacidade = float(rajada)
        self.relogio = relogio
        self.baldes: dict[str, _Balde] = {}
        self._proxima_limpeza = relogio() + self.INTERVALO_LIMPEZA

    def consumir(self, chave: str) -> float:
        """Retorna 0 se a requisição pode passar; senão, quantos segundos faltam para liberar."""
        agora = self.relogio()
        if agora >= self._proxima_limpeza:
            self._limpar(agora)

        balde = self.baldes.get(chave)
        if balde is None:
            balde = self.baldes[chave] = _Balde(self.capacidade, agora)
        else:
            balde.fichas = min(self.capacidade, balde.fichas + (agora - balde.atualizado_em) * self.taxa_por_segundo)
            balde.atualizado_em = agora

        if balde.fichas >= 1:
            balde.fichas -= 1
            return 0.0
        return (1 - balde.fichas) / self.taxa_por_segundo

    def _limpar(self, agora: float) -> None:
        # Um balde parado há tempo suficiente para encher de novo equivale a um balde novo.
        tempo_para_encher = self.capacidade / self.taxa_por_segundo
        self.baldes = {
            chave: balde for chave, balde in self.baldes.items()
            if agora - balde.atualizado_em < tempo_para_encher
        }
        self._proxima_limpeza = agora + self.INTERVALO_LIMPEZA


class ProtecaoContraSobrecarga:
    def __init__(
        self,
        app,
        *,
        max_simultaneas: int,
        por_minuto: int,
        rajada: int,
        login_por_minuto: int,
        login_rajada: int,
        max_logins_simultaneos: int,
        max_escritas_na_fila: int,
        relogio: Callable[[], float] = time.monotonic,
    ):
        self.app = app
        self.max_simultaneas = max_simultaneas
        self.max_logins_simultaneos = max_logins_simultaneos
        self.max_escritas_na_fila = max_escritas_na_fila
        self.geral = LimitadorPorCliente(por_minuto, rajada, relogio)
        self.login = LimitadorPorCliente(login_por_minuto, login_rajada, relogio)
        self.em_andamento = 0
        self.logins_em_andamento = 0
        self.escritas_na_fila = 0
        self._vez_de_gravar = asyncio.Semaphore(1)  # libera os que esperam em ordem de chegada

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        cliente = scope.get("client")
        ip = cliente[0] if cliente else "desconhecido"
        e_login = scope["path"] == ROTA_LOGIN
        e_escrita = scope["method"] in METODOS_DE_ESCRITA and not e_login

        espera = (self.login if e_login else self.geral).consumir(ip)
        if espera:
            await _responder(
                send, 429, "Muitas requisições em pouco tempo. Aguarde alguns segundos e tente novamente.",
                math.ceil(espera),
            )
            return
        if (
            self.em_andamento >= self.max_simultaneas
            or (e_login and self.logins_em_andamento >= self.max_logins_simultaneos)
            or (e_escrita and self.escritas_na_fila >= self.max_escritas_na_fila)
        ):
            await _responder(send, 503, "Servidor ocupado no momento. Tente novamente em instantes.", 1)
            return

        self.em_andamento += 1
        self.logins_em_andamento += e_login
        self.escritas_na_fila += e_escrita
        try:
            if e_escrita:
                async with self._vez_de_gravar:
                    await self.app(scope, receive, send)
            else:
                await self.app(scope, receive, send)
        finally:
            self.em_andamento -= 1
            self.logins_em_andamento -= e_login
            self.escritas_na_fila -= e_escrita


async def _responder(send, status: int, mensagem: str, tentar_em_segundos: int) -> None:
    corpo = json.dumps({"detail": mensagem}, ensure_ascii=False).encode()
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(corpo)).encode()),
            (b"retry-after", str(max(1, tentar_em_segundos)).encode()),
        ],
    })
    await send({"type": "http.response.body", "body": corpo})
