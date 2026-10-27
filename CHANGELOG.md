# 2.9.0 — Render + Supabase

- Driver Psycopg 3, normalização da URL PostgreSQL e SSL padrão.
- Pool de conexões reduzido para banco externo.
- Escape de % nas configurações Alembic para senhas codificadas.
- Migração RLS PostgreSQL para impedir acesso direto sem políticas pela Data API.
- Blueprint Render no plano Free; bloqueio de SQLite no ambiente Render.
- Guia de configuração sem publicar credenciais no código.

# 2.8.0 — Preparação Docker e deploy

- Dockerfile com usuário sem privilégios, healthcheck e execução da API/interface.
- Compose com volume SQLite, reinício automático e logs rotativos.
- Inicialização sem interação: migrations e criação condicional do primeiro administrador.
- Configurador privado, backup consistente e guia de migração/deploy.
- Publicação na internet pendente da escolha de hospedagem.

# 2.7.0 — Front-end integrado

- Interface responsiva em português, dashboard, pedidos, cargas, histórico, usuários e conta.
- Controle visual por perfil, tratamento de erros e expiração de sessão.
- Vínculo de pedidos, transições de status, filtros, paginação e exportação CSV.
- BAT passa a abrir /interface; endpoints existentes preservados.
- Sem dependências de frontend ou compilação.

# Histórico de versões

## 2.6.0

### Novidades
- **`iniciar.bat`**: instala e inicia a API em qualquer Windows com Python 3.11+ (cria o `.venv`,
  instala as dependências, gera o `.env`, aplica as migrations, cria o Administrador e oferece dados
  de demonstração). Suporta instalação sem internet (pasta `pacotes`).
- **Rate limit** (`app/protecao.py`): limite por IP, limite próprio para login, teto de logins
  simultâneos, fila de gravação e teto global de requisições simultâneas. Configurável pelo `.env`.
  Valores definidos a partir do teste de carga (ver `RELATORIO_CARGA.md`).
- **Teste de carga** (`ferramentas/teste_carga.py`): mede vazão, latência e falhas por cenário.
- **Troca da própria senha**: `PATCH /auth/senha`.
- **Listagens com filtros e paginação**: `GET /pedidos?status=&sem_carga=&offset=&limite=` e
  `GET /cargas?status=&offset=&limite=`; o total vem no cabeçalho `X-Total-Count`.
- **Dados de demonstração**: `python -m scripts.popular_demo` (30 pedidos e 7 cargas).

### Regras de negócio
- "Carregado", "Em transporte" e "Entregue" só são definidos pela carga, nunca manualmente.
- Pedido vinculado a uma carga só pode ser **cancelado** manualmente; ao cancelar, sai da carga.
- Desvincular um pedido o devolve para "Pendente" (com registro no histórico).
- Cancelar uma carga libera os pedidos dela, que voltam para "Pendente".
- Não é possível excluir um pedido vinculado a uma carga.

### Segurança e robustez
- **Corrigido travamento sob carga**: com ~100 requisições simultâneas ao banco, a API parava de
  responder por completo (pool de conexões esgotado enquanto as threads esperavam umas pelas outras).
  O pool do SQLite agora nunca faz uma requisição esperar por conexão.
- Servidor com vários processos (`LOGIFLOW_PROCESSOS`) e parser HTTP em C (`httptools`): cerca de
  2,5x mais requisições por segundo; se um processo cair, o uvicorn sobe outro.
- Trocar ou redefinir a senha invalida os tokens emitidos antes da troca.
- SQLite em modo WAL, com espera por bloqueio e fila de gravação por processo: gravações simultâneas
  não falham mais com "database is locked".
- O `iniciar.bat` se recusa a iniciar se a porta já estiver em uso (no Windows, dois servidores
  conseguem abrir a mesma porta e dividir as conexões, inclusive um antigo esquecido aberto).
- Caminho do banco SQLite relativo à pasta do projeto (antes dependia da pasta de onde o comando era executado).
- Dependências com versões fixas (testadas).

### Atenção ao atualizar
- Usuários precisam fazer login de novo (tokens antigos não têm a versão da senha).
- Exige Python 3.11 ou superior.

## 2.5.1 (refatoração)

- Correções: `PUT /cargas` com `data_saida` dava erro 500; textos só com espaços eram aceitos;
  `null` em campo obrigatório dava 409 em vez de 422; criação aceitava qualquer status; login
  revelava pelo tempo de resposta se o usuário existia; `/database/status` expunha detalhes do erro;
  chave JWT de exemplo era aceita.
- Permissões declaradas por rota, erros de regra de negócio tratados de forma central,
  dashboard com 3 consultas em vez de 18, suíte de testes automatizados.
