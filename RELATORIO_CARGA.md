# Relatório de teste de carga — LogiFlow 2.6.0

**Pergunta:** quantas requisições a API aguenta sem cair, e como impedir que ela caia.

## Resumo

| | Versão 2.5.0 (original) | Versão 2.6.0 |
|---|---|---|
| Comportamento sob carga | **Trava por completo** com ~100 requisições simultâneas ao banco e só volta minutos depois | Não trava em nenhum cenário testado (até 1.600 clientes simultâneos) |
| Leitura (pedidos, dashboard) | ~220 req/s até travar | **~450 a 1.000 req/s** (4 processos), p95 ≤ 1,3 s com até 400 clientes simultâneos |
| Gravação (criar pedido) | ~60 a 180 req/s, com erros "database is locked" | ~95 req/s com p95 de 0,2 s; acima disso responde 503 rápido, sem erros 500 |
| Login | ~20 a 30 req/s; uma enxurrada de logins deixa a API sem responder | Mesmo custo por login, mas o excesso é recusado e a API segue respondendo |
| Logo depois de uma enxurrada | Servidor ocupado por quase 1 minuto | **Responde em 26 ms** |

## Ambiente

- AMD Ryzen 5 5600X (6 núcleos / 12 threads), 16 GB, Windows 11, Python 3.14, SQLite em arquivo.
- API iniciada como no `iniciar.bat` (uvicorn), banco com os dados de demonstração.
- O gerador de carga (`ferramentas/teste_carga.py`) roda **no mesmo computador** e disputa CPU com a
  API, então os números são conservadores. Execuções repetidas variaram até ~40%; use as faixas, não
  os valores exatos.
- Cada nível dura 10 s. "Aguenta" = menos de 1% de falhas e 95% das respostas em menos de 2 s (p95).
- Falhas = tempo esgotado (10 s), conexão recusada ou erro 500. Respostas 429/503 do rate limit são
  contadas à parte: são recusas propositais e rápidas.

## 1. Versão original: a API trava

Leitura de pedidos (`GET /pedidos`), 1 processo:

| Clientes simultâneos | Atendidas | p95 | Situação |
|---|---|---|---|
| 1 | 195 req/s | 6 ms | ok |
| 10 | 216 req/s | 62 ms | ok |
| 50 | 227 req/s | 338 ms | ok |
| **100** | **0** | — | **travou**: nenhuma resposta, e o servidor continuou sem responder minutos depois da carga parar |

**Causa:** o pool de conexões do SQLAlchemy tinha 15 conexões e as rotas rodam num grupo de 40
threads. Com 100 requisições, as 40 threads ficavam esperando uma conexão, enquanto as requisições
que seguravam as conexões precisavam de uma thread livre para terminar e devolvê-las. Ninguém
andava até o tempo limite de 30 s (`QueuePool limit of size 5 overflow 10 reached`, 200 vezes no log).

**Correção:** o pool do SQLite agora cria conexões extras em vez de fazer esperar (`app/database.py`).
Sem o banco (`GET /status`), a API já aguentava ~1.000 req/s; o problema era só o pool.

## 2. Capacidade depois da correção (sem rate limit)

1 processo:

| Cenário | Vazão | p95 com 100 clientes | p95 com 400 clientes | Com 1.600 clientes |
|---|---|---|---|---|
| Leitura | ~220 req/s | 0,58 s | 2,4 s | 1.145 falhas |
| Dashboard | ~255 req/s | 0,42 s | 2,3 s | 1.262 falhas |
| Gravação | ~60 a 180 req/s | 1,5 s | 4,2 s | 2.628 falhas |
| Login | ~20 a 30 req/s | 5,1 s | todos com tempo esgotado | nenhum atendido |

4 processos (`LOGIFLOW_PROCESSOS=4`) + parser `httptools`:

| Cenário | Vazão | p95 com 100 clientes | p95 com 400 clientes |
|---|---|---|---|
| Leitura | ~550 a 1.000 req/s | 0,14 s | 0,66 s |
| Dashboard | ~230 a 520 req/s | 0,4 a 1,0 s | 1,1 a 2,5 s |
| Gravação | ~100 a 120 req/s | 4,2 s (e 1 erro "database is locked") | 6,7 s |
| Login | ~28 a 31 req/s | 3,4 s | todos com tempo esgotado |

Sem rate limit a API **não trava mais**, mas acima da capacidade a fila cresce sem limite: as
respostas demoram até estourar o tempo, e depois de uma enxurrada de 1.600 logins o servidor
**ficou quase 1 minuto sem responder**, processando logins que ninguém mais esperava.

**Resposta à pergunta:** neste computador, com 4 processos, a API sustenta cerca de **500 leituras por
segundo com até 400 usuários simultâneos**, **~100 gravações por segundo** (limite do SQLite) e **~30
logins por segundo** (o hash de senha Argon2 é caro de propósito). Num computador de serviço mais
simples, espere menos: rode a ferramenta nele para obter o número real.

## 3. Rate limit

Com base nesses números, `app/protecao.py` adiciona cinco proteções (valores por processo, no `.env`):

| Proteção | Valor | Por quê |
|---|---|---|
| Limite por IP | 300/min, rajada de 60 | Um usuário real faz poucas requisições por segundo; um script descontrolado é contido sem afetar os outros |
| Login por IP | 10/min, rajada de 5 | Contra força bruta: no máximo 10 tentativas de senha por minuto |
| Logins simultâneos | 10 | Com 10 logins simultâneos o p95 ficou em 0,6 s; acima disso o login tomaria a CPU das outras rotas |
| Fila de gravação | 20 | As gravações de cada processo esperam a vez em ordem; acabou o "database is locked" |
| Requisições simultâneas | 100 | Com 100 em andamento a leitura ficou com p95 ≤ 0,6 s mesmo em 1 processo |

Acima dos limites a API responde **429** (por IP, com `Retry-After`) ou **503** (servidor cheio) na hora,
em vez de enfileirar.

### Resultado com o rate limit (4 processos, cada cliente com IP próprio)

**Pior caso — clientes que ignoram o 429/503 e repetem sem parar** (como um ataque):

| Cenário | 100 clientes | 400 clientes | 1.600 clientes |
|---|---|---|---|
| Leitura | 488 req/s, p95 0,33 s | 431 req/s, p95 1,24 s | 25 req/s (o servidor gasta a CPU recusando ~1.900 req/s) |
| Dashboard | 518 req/s, p95 0,37 s | 428 req/s, p95 1,15 s | 50 req/s |
| Gravação | 60 req/s, p95 4,1 s | 6 req/s | 1 req/s |
| Login | 13 req/s aceitos, resto recusado | 10 req/s | 8 req/s |

Erros 500: **0**. Logo depois da enxurrada, `/status` respondeu em **26 ms**.

**Uso real — clientes que respeitam o `Retry-After`** (como o navegador, o Swagger ou um sistema
bem-feito, que esperam antes de tentar de novo):

| Cenário | 100 clientes | 400 clientes | 1.600 clientes |
|---|---|---|---|
| Leitura | 486 req/s, p95 0,32 s | 374 req/s, p95 0,99 s | **193 req/s, p95 2,9 s, 0 falhas** |
| Dashboard | 515 req/s, p95 0,29 s | 464 req/s, p95 1,02 s | **245 req/s, p95 2,8 s, 0 falhas** |
| Gravação | 113 req/s, p95 1,9 s, 0 falhas | 87 req/s, p95 2,2 s, 0 falhas | 25 req/s, 0 falhas |
| Login | 15 req/s, p95 4,1 s | 12 req/s, p95 3,2 s | 8 req/s, 0 falhas |

Erros 500: **0**. Logo depois da carga, `/status` respondeu em **31 ms**.

Com usuários reais a API atende de forma estável mesmo com 1.600 clientes simultâneos: quem passa do
limite espera um pouco e é atendido, em vez de derrubar o serviço para todos.

**Login:** com `LIMITE_LOGINS_SIMULTANEOS=4` cada login responde mais rápido (p95 1,6 s com 100
clientes), mas o servidor atende menos logins por segundo (8 contra 15). O padrão 10 favorece o pico
de começo de turno, quando todos entram ao mesmo tempo: 400 pessoas entram em ~30 s, contra ~48 s.

## 4. Limites que o rate limit não resolve

- **Enxurradas que ignoram as recusas.** Recusar também custa CPU. Com 1.600 clientes martelando,
  a API continua no ar e volta ao normal na hora, mas atende pouco enquanto a enxurrada dura.
  Proteção contra isso é de rede: firewall ou proxy reverso (nginx, IIS) na frente da API.
- **Gravações.** O SQLite grava uma coisa por vez (~100 gravações/s). Para mais do que isso, use PostgreSQL.
- **Proxy reverso.** O limite por IP usa o IP da conexão; atrás de um proxy, todos os usuários teriam
  o IP do proxy e dividiriam o mesmo limite.
- **Vários processos.** Cada processo conta seus próprios limites, então o limite por IP pode chegar
  a N vezes o configurado (N = processos).

## Como repetir o teste

Com a API rodando **com um banco de teste** (o cenário de gravação cria pedidos `TESTE-CARGA-*`):

```powershell
.\.venv\Scripts\python.exe -m ferramentas.teste_carga --usuario admin --cenarios leitura,dashboard,login
.\.venv\Scripts\python.exe -m ferramentas.teste_carga --usuario admin --cenarios escrita --permitir-escrita
```

Opções úteis: `--clientes 10,100,400`, `--duracao 10`, `--ips-distintos` (simula computadores
diferentes; só com a API em 127.0.0.1), `--respeitar-retry-after` (clientes bem-comportados) e
`--saida resultados_carga.json`.
