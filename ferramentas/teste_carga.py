"""Teste de carga do LogiFlow: mede quantas requisições por segundo a API aguenta.

Com a API rodando (de preferência com um banco de teste, não o da operação):

    python -m ferramentas.teste_carga --usuario admin
    python -m ferramentas.teste_carga --usuario admin --cenarios leitura --clientes 10,100,400

Para cada cenário, aumenta o número de clientes simultâneos e mede vazão,
latência e falhas. A API "aguenta" um nível quando menos de 1% das
requisições falham e 95% das atendidas respondem em menos de 2 s.
Respostas 429/503 do rate limit são contadas à parte: são recusas
propositais e rápidas, não falhas.

Usa só a biblioteca padrão. O cliente HTTP é mínimo de propósito: clientes
genéricos (como o httpx) ficaram mais lentos que a própria API nos testes e
mediam o cliente em vez do servidor. A carga é dividida entre processos.
"""
import argparse
import asyncio
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from getpass import getpass

CENARIOS = {
    "status": "GET /status (sem banco e sem login)",
    "leitura": "GET /pedidos?limite=20 (autenticado, lê do banco)",
    "dashboard": "GET /dashboard/resumo (autenticado, agregações)",
    "login": "POST /auth/login (hash Argon2, pesado de CPU)",
    "escrita": "POST /pedidos (grava no banco; exige --permitir-escrita)",
}
LIMITE_FALHAS = 0.01
LIMITE_P95_SEGUNDOS = 2.0


@dataclass
class Resultado:
    cenario: str
    clientes: int
    duracao_s: float
    total: int
    atendidas: int
    recusadas: int
    falhas: int
    vazao_rps: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    codigos: dict
    aguenta: bool


# ----------------------------------------------------------------- cliente HTTP mínimo

def montar_requisicao(cenario: str, host: str, token: str, credenciais: str) -> bytes:
    cabecalhos = [f"Host: {host}", "Connection: keep-alive"]
    if cenario not in {"status", "login"}:
        cabecalhos.append(f"Authorization: Bearer {token}")

    if cenario == "status":
        linha, corpo = "GET /status", b""
    elif cenario == "leitura":
        linha, corpo = "GET /pedidos?limite=20", b""
    elif cenario == "dashboard":
        linha, corpo = "GET /dashboard/resumo", b""
    elif cenario == "login":
        linha, corpo = "POST /auth/login", credenciais.encode()
        cabecalhos.append("Content-Type: application/x-www-form-urlencoded")
    else:
        linha = "POST /pedidos"
        corpo = json.dumps({
            "numero_pedido": f"TESTE-CARGA-{uuid.uuid4().hex[:12]}",
            "cliente": "Teste de carga",
            "cidade": "Campinas",
            "uf": "SP",
            "peso": 1,
            "valor_total": 1,
        }).encode()
        cabecalhos.append("Content-Type: application/json")

    if corpo:
        cabecalhos.append(f"Content-Length: {len(corpo)}")
    return (f"{linha} HTTP/1.1\r\n" + "\r\n".join(cabecalhos) + "\r\n\r\n").encode() + corpo


async def ler_resposta(leitor: asyncio.StreamReader) -> tuple[int, bool, float]:
    """Lê uma resposta HTTP/1.1 inteira. Retorna (status, servidor pediu para fechar, Retry-After em s)."""
    cabecalho = (await leitor.readuntil(b"\r\n\r\n")).decode("latin-1").split("\r\n")
    status = int(cabecalho[0].split(" ", 2)[1])
    tamanho, fechar, em_blocos, tentar_em = 0, False, False, 0.0
    for linha in cabecalho[1:]:
        nome, _, valor = linha.partition(":")
        nome, valor = nome.strip().lower(), valor.strip().lower()
        if nome == "content-length":
            tamanho = int(valor)
        elif nome == "connection" and valor == "close":
            fechar = True
        elif nome == "transfer-encoding" and "chunked" in valor:
            em_blocos = True
        elif nome == "retry-after" and valor.isdigit():
            tentar_em = float(valor)

    if em_blocos:
        while True:
            tamanho_bloco = int((await leitor.readuntil(b"\r\n")).strip(), 16)
            await leitor.readexactly(tamanho_bloco + 2)
            if tamanho_bloco == 0:
                break
    elif tamanho:
        await leitor.readexactly(tamanho)
    return status, fechar, tentar_em


async def rodar_clientes(config: dict) -> tuple[dict, list[float]]:
    host, porta = config["host"], config["porta"]
    codigos: Counter = Counter()
    latencias: list[float] = []

    espera = config["inicio_em"] - time.time()
    if espera > 0:
        await asyncio.sleep(espera)
    fim = time.perf_counter() + config["duracao"]

    async def usuario_simulado(indice: int):
        # Com --ips-distintos, cada cliente sai de um IP de loopback próprio (127.0.x.y),
        # como se fossem computadores diferentes; o rate limit por IP passa a valer por cliente.
        origem = (f"127.0.{1 + indice // 250}.{2 + indice % 250}", 0) if config["ips_distintos"] else None
        leitor = escritor = None
        while time.perf_counter() < fim:
            inicio = time.perf_counter()
            try:
                if escritor is None:
                    leitor, escritor = await asyncio.wait_for(
                        asyncio.open_connection(host, porta, local_addr=origem), config["timeout"],
                    )
                escritor.write(montar_requisicao(config["cenario"], f"{host}:{porta}", config["token"], config["credenciais"]))
                status, fechar, tentar_em = await asyncio.wait_for(ler_resposta(leitor), config["timeout"])
            except asyncio.TimeoutError:
                codigos["timeout"] += 1
                status, fechar, tentar_em = None, True, 0.0
            except (OSError, asyncio.IncompleteReadError, asyncio.LimitOverrunError, ValueError):
                codigos["erro_conexao"] += 1
                status, fechar, tentar_em = None, True, 0.0
                await asyncio.sleep(0.05)
            else:
                codigos[status] += 1
                if 200 <= status < 300:
                    latencias.append(time.perf_counter() - inicio)
            if fechar and escritor is not None:
                escritor.close()
                leitor = escritor = None
            if config["respeitar_retry_after"] and status in (429, 503):
                # Cliente bem-comportado: espera o tempo pedido pelo servidor antes de tentar de novo.
                await asyncio.sleep(min(tentar_em or 1.0, max(0.0, fim - time.perf_counter())))
        if escritor is not None:
            escritor.close()

    primeiro = config["indice_inicial"]
    await asyncio.gather(*(usuario_simulado(primeiro + i) for i in range(config["clientes"])))
    return dict(codigos), latencias


def processo_de_carga(config: dict) -> tuple[dict, list[float]]:
    return asyncio.run(rodar_clientes(config))


# ----------------------------------------------------------------- medição

def percentil(valores: list[float], fracao: float) -> float:
    if not valores:
        return 0.0
    return valores[min(len(valores) - 1, int(fracao * len(valores)))]


def executar_nivel(executor, args, cenario: str, clientes: int, token: str) -> Resultado:
    processos = max(1, min(args.processos, clientes))
    divisao = [clientes // processos + (1 if i < clientes % processos else 0) for i in range(processos)]
    url = urllib.parse.urlsplit(args.url)
    base = {
        "host": url.hostname,
        "porta": url.port or 80,
        "cenario": cenario,
        "duracao": args.duracao,
        "timeout": args.timeout,
        "token": token,
        "credenciais": urllib.parse.urlencode({"username": args.usuario, "password": args.senha}),
        "ips_distintos": args.ips_distintos,
        "respeitar_retry_after": args.respeitar_retry_after,
        "inicio_em": time.time() + 1.5,  # todos os processos começam juntos
    }
    inicios = [sum(divisao[:i]) for i in range(processos)]
    futuros = [
        executor.submit(processo_de_carga, base | {"clientes": n, "indice_inicial": inicio})
        for n, inicio in zip(divisao, inicios)
    ]

    codigos: Counter = Counter()
    latencias: list[float] = []
    for futuro in futuros:
        parcial, tempos = futuro.result()
        codigos.update(parcial)
        latencias.extend(tempos)
    latencias.sort()

    total = sum(codigos.values())
    atendidas = sum(n for codigo, n in codigos.items() if isinstance(codigo, int) and 200 <= codigo < 300)
    recusadas = codigos.get(429, 0) + codigos.get(503, 0)
    falhas = total - atendidas - recusadas
    p95 = percentil(latencias, 0.95)
    return Resultado(
        cenario=cenario,
        clientes=clientes,
        duracao_s=args.duracao,
        total=total,
        atendidas=atendidas,
        recusadas=recusadas,
        falhas=falhas,
        vazao_rps=round(atendidas / args.duracao, 1),
        p50_ms=round(percentil(latencias, 0.50) * 1000, 1),
        p95_ms=round(p95 * 1000, 1),
        p99_ms=round(percentil(latencias, 0.99) * 1000, 1),
        codigos={str(codigo): n for codigo, n in sorted(codigos.items(), key=lambda item: str(item[0]))},
        aguenta=total > 0 and falhas / total < LIMITE_FALHAS and p95 < LIMITE_P95_SEGUNDOS,
    )


def servidor_respondendo(url: str) -> bool:
    for _ in range(10):
        try:
            with urllib.request.urlopen(f"{url}/status", timeout=5) as resposta:
                if resposta.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(1)
    return False


def obter_token(args) -> str:
    dados = urllib.parse.urlencode({"username": args.usuario, "password": args.senha}).encode()
    with urllib.request.urlopen(f"{args.url}/auth/login", data=dados, timeout=30) as resposta:
        return json.load(resposta)["access_token"]


def imprimir(resultado: Resultado) -> None:
    situacao = "OK" if resultado.aguenta else "NAO AGUENTA"
    print(
        f"  {resultado.clientes:>5} clientes | {resultado.vazao_rps:>8.1f} req/s atendidas | "
        f"p50 {resultado.p50_ms:>7.1f} ms | p95 {resultado.p95_ms:>8.1f} ms | "
        f"recusadas {resultado.recusadas:>6} | falhas {resultado.falhas:>6} | {situacao}",
        flush=True,
    )


def principal(args) -> list[Resultado]:
    token = obter_token(args)
    resultados: list[Resultado] = []
    with ProcessPoolExecutor(max_workers=args.processos) as executor:
        for cenario in args.cenarios:
            print(f"\n== {cenario}: {CENARIOS[cenario]}", flush=True)
            for clientes in args.clientes:
                if cenario != "login":
                    token = obter_token(args)  # renova o token a cada nível (ele expira)
                resultado = executar_nivel(executor, args, cenario, clientes, token)
                resultados.append(resultado)
                imprimir(resultado)
                if not servidor_respondendo(args.url):
                    print("  !! O servidor parou de responder. Interrompendo o teste.")
                    return resultados
                time.sleep(args.pausa)

    print("\nMaior vazão sustentada (menos de 1% de falhas e p95 < 2 s):")
    for cenario in args.cenarios:
        aprovados = [r for r in resultados if r.cenario == cenario and r.aguenta]
        if aprovados:
            melhor = max(aprovados, key=lambda r: r.vazao_rps)
            print(f"  {cenario:<10} {melhor.vazao_rps:>8.1f} req/s (com {melhor.clientes} clientes simultâneos)")
        else:
            print(f"  {cenario:<10} nenhum nível aprovado")
    return resultados


def ler_argumentos():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--usuario", required=True)
    parser.add_argument("--senha", help="Se omitida, é perguntada sem aparecer na tela.")
    parser.add_argument("--cenarios", default="status,leitura,dashboard,login",
                        help=f"Separados por vírgula. Opções: {', '.join(CENARIOS)}.")
    parser.add_argument("--clientes", default="1,10,50,100,200,400,800",
                        help="Níveis de clientes simultâneos, separados por vírgula.")
    parser.add_argument("--duracao", type=float, default=10, help="Segundos em cada nível.")
    parser.add_argument("--timeout", type=float, default=10, help="Segundos até considerar a requisição perdida.")
    parser.add_argument("--pausa", type=float, default=2, help="Segundos de descanso entre níveis.")
    parser.add_argument("--processos", type=int, default=min(4, os.cpu_count() or 1),
                        help="Processos que geram a carga (para o cliente não virar o gargalo).")
    parser.add_argument("--permitir-escrita", action="store_true",
                        help="Libera o cenário 'escrita', que cria pedidos TESTE-CARGA-* no banco.")
    parser.add_argument("--ips-distintos", action="store_true",
                        help="Cada cliente usa um IP de loopback próprio (só para API em 127.0.0.1), "
                             "simulando computadores diferentes para o rate limit por IP.")
    parser.add_argument("--respeitar-retry-after", action="store_true",
                        help="Ao receber 429/503, o cliente espera o Retry-After antes de tentar de novo "
                             "(como um navegador ou sistema bem-feito). Sem a opção, os clientes martelam "
                             "sem pausa: é o pior caso, parecido com um ataque.")
    parser.add_argument("--saida", help="Grava os resultados em JSON neste arquivo.")
    args = parser.parse_args()

    args.url = args.url.rstrip("/")
    args.cenarios = [c.strip() for c in args.cenarios.split(",") if c.strip()]
    desconhecidos = set(args.cenarios) - set(CENARIOS)
    if desconhecidos:
        parser.error(f"cenário desconhecido: {', '.join(sorted(desconhecidos))}")
    if "escrita" in args.cenarios and not args.permitir_escrita:
        parser.error("o cenário 'escrita' cria pedidos no banco; use --permitir-escrita (de preferência num banco de teste)")
    args.clientes = [int(n) for n in args.clientes.split(",")]
    if args.ips_distintos and urllib.parse.urlsplit(args.url).hostname not in {"127.0.0.1", "localhost"}:
        parser.error("--ips-distintos só funciona com a API rodando neste computador (127.0.0.1)")
    if args.senha is None:
        args.senha = getpass("Senha: ")
    return args


def main() -> None:
    args = ler_argumentos()
    resultados = principal(args)
    if args.saida:
        with open(args.saida, "w", encoding="utf-8") as arquivo:
            json.dump([asdict(r) for r in resultados], arquivo, ensure_ascii=False, indent=2)
        print(f"\nResultados gravados em {args.saida}")


if __name__ == "__main__":
    main()
