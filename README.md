# LogiFlow 2.9.0 — Render + Supabase

**Deploy gratuito: comece pelo [RENDER_SUPABASE.md](RENDER_SUPABASE.md).** Inclui PostgreSQL/Psycopg com SSL, pool reduzido, RLS para acesso direto e Blueprint Render Free com variáveis privadas. Mantém SQLite para uso local.

O ZIP não foi publicado automaticamente. Precisamos conectar as contas, configurar DATABASE_URL e validar a execução real. O banco SQLite antigo não é importado automaticamente.

---

# LogiFlow 2.8.0 — Docker

Esta versão inclui o front-end integrado da 2.7.0, Dockerfile, Compose, volume persistente, inicialização automática e backup SQLite.

**Comece pelo [DEPLOY.md](DEPLOY.md).** Para rodar no Docker: `python scripts/configurar_docker.py`, depois `docker compose up -d --build` e acesse `http://localhost:8000/interface`. Requer Docker e Compose 2.30+. O deploy público depende da escolha da hospedagem; ainda não foi publicado.

---

# LogiFlow 2.7.0 — interface operacional

## Início rápido

1. Extraia o ZIP inteiro antes de executar.
2. No Windows, dê dois cliques em `iniciar.bat` (Python 3.11 ou superior).
3. O navegador abrirá **http://127.0.0.1:8000/interface**. Mantenha a janela do servidor aberta.
4. Use seu usuário e senha. Na primeira instalação, o preparador pede o cadastro do administrador e oferece dados de demonstração.

**Atualizando uma instalação existente:** faça backup da pasta anterior, principalmente do `.env` e do banco. Pare o servidor e copie os arquivos desta versão para a instalação, preservando seu `.env` e `logiflow.db`. Não substitua seu banco por outro banco. O ZIP de origem não continha banco nem credenciais; uma extração nova inicia uma instalação nova.

## Interface disponível

- Visão geral: indicadores e barras de pedidos por status, dia e cidade, além de cargas por transportadora.
- Pedidos: cadastro, consulta, edição, observações, histórico e exclusão pelo administrador.
- Cargas: cadastro, edição, histórico, exclusão, vínculos pelo número do pedido e remoção de vínculos.
- Fluxo operacional: crie os pedidos e a carga, vincule os pedidos e avance a carga por Em carregamento → Carregada → Em transporte → Finalizada. Os pedidos acompanham as regras já implementadas na API.
- Usuários: criação, perfil, ativação/desativação e redefinição de senha pelo administrador.
- Minha conta: alteração de senha e saída da sessão.
- Consulta: somente leitura. Operação: cadastros e alterações. Administrador: também exclusões e gestão de usuários.
- Listagens paginadas em 25 registros. A busca e a exportação CSV consideram **a página atual**, conforme indicado na tela; os filtros de status e vínculo abrangem todo o banco.
- CSV com separador ponto e vírgula e UTF-8, compatível com Excel. Esta versão não exporta XLSX.
- A interface não depende de fontes, bibliotecas ou CDNs externas. A instalação inicial das dependências Python segue as opções já disponíveis no BAT.
- Sessão mantida na aba com `sessionStorage`; ao expirar, entre novamente. Atualize a tela pelo botão Atualizar para ver alterações feitas por outra pessoa.

Para acesso pela rede, defina `LOGIFLOW_HOST=0.0.0.0` no BAT e use `http://IP-DO-SERVIDOR:8000/interface`. A documentação da API permanece em `/docs`, e o endpoint `/` foi preservado.

## Código da interface

`app/static/index.html`, `app/static/style.css` e `app/static/app.js`. Arquivos completos, sem etapa de compilação. O FastAPI serve a interface em `/interface` e seus arquivos em `/interface/arquivos`.

## Validação desta entrega

88 testes anteriores aprovados e 2 testes adicionais de disponibilização da interface e proteção dos dados. Fluxo de formulários validado com DOM simulado e API real. Conferência visual em navegador não concluída neste ambiente; a instalação do navegador de testes falhou no download.

---

## Documentação anterior (base 2.6.0)

# LogiFlow API — 2.6.0

API de logística para gerenciar pedidos, cargas e a operação de expedição, construída com
FastAPI, SQLAlchemy e SQLite.

## Recursos

- Cadastro de pedidos e cargas, com vínculo entre eles e peso total da carga calculado automaticamente
- Fluxo de status com transições validadas e sincronização automática pedido ↔ carga
- Histórico (auditoria) de todas as mudanças de status, com a origem de cada mudança
- Dashboard com indicadores, pedidos por cidade, cargas por transportadora e pedidos por dia
- Autenticação JWT, perfis **Administrador**, **Operação** e **Consulta** e administração de usuários
- Listagens com filtros e paginação
- Rate limit e proteção contra sobrecarga, calibrados por teste de carga
- Instalação e inicialização com um clique no Windows (`iniciar.bat`)

## Como rodar (Windows)

Pré-requisito: **Python 3.11 ou superior** instalado, com a opção *"Add python.exe to PATH"* marcada
(<https://www.python.org/downloads/>).

1. Copie a pasta do projeto para o computador (de preferência num caminho curto, como `C:\LogiFlow`).
2. Dê dois cliques em **`iniciar.bat`**.

Na primeira execução o `.bat` cria o ambiente Python, instala as dependências, gera o `.env` com uma
chave nova, cria o banco, pede os dados do primeiro **Administrador** e oferece carregar dados de
demonstração. Depois abre o Swagger em `http://127.0.0.1:8000/docs`. Nas próximas vezes ele só inicia a API.

Para encerrar, feche a janela ou pressione `Ctrl+C`.

### Opções do `iniciar.bat`

Edite o início do arquivo ou defina as variáveis antes de executar:

| Variável | Padrão | Para que serve |
|---|---|---|
| `LOGIFLOW_HOST` | `127.0.0.1` | Use `0.0.0.0` para outros computadores da rede acessarem (o Windows pode pedir liberação no firewall) |
| `LOGIFLOW_PORTA` | `8000` | Porta da API |
| `LOGIFLOW_PROCESSOS` | metade dos núcleos (1 a 4) | Processos do servidor: mais processos atendem mais requisições e usam mais memória (~100 MB cada) |

**Sem internet nos computadores do serviço:** num computador com internet e a **mesma versão do
Python**, rode `pip download -r requirements.txt -d pacotes` e copie a pasta `pacotes` para dentro do
projeto. O `.bat` instala a partir dela. Atrás de um proxy corporativo, defina `HTTPS_PROXY` antes de executar.

## Como usar

1. Abra `http://127.0.0.1:8000/docs`, clique em **Authorize** e entre com o usuário e a senha do Administrador.
2. Crie os demais usuários em `POST /usuarios` (perfis `Operação` e `Consulta`).
3. Cadastre pedidos e cargas, vincule pedidos a cargas e avance o status da carga: os pedidos acompanham.

Cada usuário pode trocar a própria senha em `PATCH /auth/senha`. Trocar ou redefinir uma senha
encerra as sessões abertas com a senha antiga.

### Perfis

| Perfil | Pode |
|---|---|
| Consulta | Ler pedidos, cargas, históricos e dashboard |
| Operação | Tudo do Consulta + criar e alterar pedidos e cargas, vincular e desvincular pedidos |
| Administrador | Tudo + excluir pedidos e cargas e administrar usuários |

### Regras de status

- **Pedido:** Pendente → Em separação → Carregado → Em transporte → Entregue (ou Cancelado até sair para transporte).
- **Carga:** Planejada → Em carregamento → Carregada → Em transporte → Finalizada (ou Cancelada até sair para transporte).
- Ao avançar a carga, os pedidos dela avançam junto. "Carregado", "Em transporte" e "Entregue" só são
  definidos pela carga, nunca manualmente.
- Pedido dentro de uma carga só pode ser **cancelado** manualmente; ao ser cancelado, sai da carga.
- Desvincular um pedido, ou cancelar a carga, devolve os pedidos para "Pendente".
- Só se adicionam pedidos a cargas "Planejada" ou "Em carregamento"; uma carga só sai para transporte com pedidos.
- Não se exclui carga com pedidos nem pedido vinculado a carga.

## Instalação manual (outros sistemas ou desenvolvimento)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m scripts.preparar
python -m uvicorn app.main:app --reload
```

`scripts.preparar` cria o `.env`, aplica as migrations (`alembic upgrade head`), cria o Administrador e
oferece os dados de demonstração. Os passos também podem ser feitos separadamente: `alembic upgrade head`,
`python -m scripts.criar_admin` e `python -m scripts.popular_demo`.

## Configuração (`.env`)

| Variável | Padrão | Descrição |
|---|---|---|
| `JWT_SECRET_KEY` | (gerada pelo `.bat`) | Chave dos tokens, com no mínimo 32 caracteres |
| `JWT_EXPIRE_MINUTES` | `60` | Validade do login |
| `DATABASE_URL` | `sqlite:///./logiflow.db` | Banco de dados (caminho relativo à pasta do projeto) |
| `LIMITE_ATIVO` | `true` | Liga ou desliga o rate limit |
| `LIMITE_SIMULTANEAS` | `100` | Requisições em andamento por processo; acima disso responde 503 |
| `LIMITE_POR_MINUTO` / `LIMITE_RAJADA` | `300` / `60` | Requisições por minuto por IP e rajada permitida; acima disso responde 429 |
| `LIMITE_LOGIN_POR_MINUTO` / `LIMITE_LOGIN_RAJADA` | `10` / `5` | O mesmo, só para o login (proteção contra força bruta) |
| `LIMITE_LOGINS_SIMULTANEOS` | `10` | Logins em andamento por processo |
| `LIMITE_ESCRITAS_NA_FILA` | `20` | Gravações aguardando a vez por processo (elas são atendidas uma de cada vez) |

## Capacidade e rate limit

Medido com `ferramentas/teste_carga.py` num Ryzen 5 5600X com 4 processos (detalhes, metodologia e
limitações em [`RELATORIO_CARGA.md`](RELATORIO_CARGA.md)):

| Operação | Capacidade aproximada | Com 400 usuários simultâneos |
|---|---|---|
| Leitura (listas, dashboard) | 450 a 1.000 req/s | p95 ≈ 1 s |
| Gravação (criar/alterar) | ~100 req/s (limite do SQLite) | p95 ≈ 2 s |
| Login | ~30 req/s (hash Argon2) | excesso recebe 503 e tenta de novo |

A versão 2.5.0 **travava por completo** com ~100 requisições simultâneas ao banco. Na 2.6.0 a causa
foi corrigida e o rate limit (`app/protecao.py`) recusa o excesso na hora, com **429** (limite por IP,
com `Retry-After`) ou **503** (servidor cheio), em vez de enfileirar até estourar o tempo. Nos testes,
com até 1.600 clientes simultâneos não houve nenhum erro 500, e a API respondeu em ~30 ms logo depois
de cada enxurrada.

Para medir no computador onde a API vai rodar (use um banco de teste: o cenário de gravação cria pedidos):

```powershell
.\.venv\Scripts\python.exe -m ferramentas.teste_carga --usuario admin --cenarios leitura,dashboard,login
```

## Testes

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```

Os testes usam um banco em memória e não tocam no `logiflow.db`.

## Segurança

- O `.env` e o banco local não vão para o Git. Nunca publique a `JWT_SECRET_KEY`.
- Faça backup do arquivo `logiflow.db` (com a API parada, ou copiando também `logiflow.db-wal`).
- O SQLite atende bem uma operação de porte pequeno ou médio num único servidor. Para muitos acessos
  simultâneos de gravação, o caminho é o PostgreSQL: instale o driver (`pip install "psycopg[binary]"`)
  e defina `DATABASE_URL=postgresql+psycopg://usuario:senha@servidor/logiflow`.
