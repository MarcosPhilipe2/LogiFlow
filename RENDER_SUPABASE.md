# Publicar LogiFlow no Render Free + Supabase Free

Este é o caminho de nuvem da versão 2.9.0. O Docker Compose continua disponível para rodar SQLite localmente; no Render a aplicação usa Dockerfile e PostgreSQL externo. Ainda é necessário criar/conectar as contas e validar um deploy real.

## 1. Supabase: banco

1. Entre em https://supabase.com/dashboard e crie um projeto novo no plano Free, chamado `logiflow`.
2. Guarde a senha do BANCO em um gerenciador de senhas. Ela não é a senha do administrador do LogiFlow.
3. Depois de o projeto ficar pronto, clique em **Connect** e selecione **Session pooler**, porta **5432**. Copie a URI e substitua `[YOUR-PASSWORD]` pela senha do banco. Caracteres reservados na senha devem ser codificados na URL (ex.: @ vira %40). Não use a URL pública do projeto nem uma chave anon/service_role no lugar da conexão PostgreSQL.
4. Essa URI será inserida SOMENTE na variável `DATABASE_URL` do Render. Não envie a senha, URI ou arquivos .env pelo chat nem coloque no GitHub.
5. Use este projeto novo somente para o LogiFlow. O navegador continuará usando o login da nossa API; não é necessário migrar para Supabase Auth.

A aplicação normaliza `postgresql://` para o driver Psycopg e ativa SSL por padrão. O Session pooler permite conectividade IPv4 e preserva sessões, necessária para o comportamento esperado desta aplicação e das migrations. A conta de conexão esperada é `postgres.<referência do projeto>` fornecida pelo painel.

As migrations criam as tabelas e ativam RLS sem políticas para a Data API do Supabase. O servidor conecta como postgres (que pode contornar RLS); o acesso dos usuários continua controlado pela API. Não exponha credenciais do banco nem crie políticas públicas de leitura das tabelas. Se não precisar da Data API, também pode desativá-la nas configurações do projeto.

## 2. GitHub: código

Publique o CONTEÚDO da pasta `LogiFlow_2.9.0` em seu repositório. O `Dockerfile`, `render.yaml`, `requirements.txt` e a pasta `app` devem ficar na raiz do repositório. Não publique `.env`, `.env.docker`, banco local ou backups. Faça backup do projeto anterior antes de atualizar.

## 3. Render: aplicação

1. Entre em https://dashboard.render.com e conecte o repositório do GitHub.
2. Escolha **New → Blueprint**, selecione o repositório e use `render.yaml`. Confira que há apenas um Web Service **Free**, sem disco e sem banco Render.
3. Preencha as variáveis solicitadas:

| Variável | Valor |
| --- | --- |
| DATABASE_URL | URI do Session pooler do Supabase |
| LOGIFLOW_ADMIN_USUARIO | Login inicial escolhido, ex.: marcos |
| LOGIFLOW_ADMIN_NOME | Nome do administrador |
| LOGIFLOW_ADMIN_SENHA | Senha inicial de 8 a 128 caracteres |

`JWT_SECRET_KEY` será gerada automaticamente pelo Blueprint. Não a publique. O serviço usa a variável `PORT` fornecida pelo Render e executa migrations antes de abrir a API. Não preencha um comando de build ou de início Python por cima do Dockerfile.

Alternativa manual: **New → Web Service**, selecione o repositório, Language **Docker**, plano **Free**, Dockerfile `./Dockerfile`, healthcheck `/status`, e cadastre também `JWT_SECRET_KEY` com 32 caracteres ou mais. Você pode gerar localmente com `python -c "import secrets; print(secrets.token_hex(32))"`.

4. Aguarde o deploy ficar disponível e abra `https://SEU-SERVICO.onrender.com/interface` (substitua pelo endereço real exibido no painel).
5. Entre com o administrador, cadastre um pedido e uma carga, vincule, avance o status e consulte o histórico/dashboard.
6. Reinicie ou republique e confirme que o pedido continua no Supabase. Isso valida a persistência externa.
7. Depois do primeiro acesso, remova `LOGIFLOW_ADMIN_SENHA` do ambiente do serviço. Não troque `JWT_SECRET_KEY` a cada deploy; os usuários e senhas já estão no banco. Alterações de senha futuras são feitas na interface.

Se você conectar as integrações Render e Supabase no ChatGPT, podemos fazer as etapas suportadas por elas. A conexão não publica sozinha nem confirma que o deploy ocorreu.

## 4. Dados antigos

Esta versão cria a estrutura num Supabase novo, mas NÃO importa automaticamente o SQLite. Não apague o banco anterior. Para levar os pedidos, cargas, usuários e histórico antigos, precisamos executar uma migração de dados separada e validar contagens, vínculos e IDs antes de substituir o uso local.

## 5. Limitações do plano gratuito

- Render pode suspender após 15 minutos sem tráfego; o primeiro acesso pode levar cerca de um minuto.
- Supabase Free pode pausar após uma semana de inatividade; nesse caso retome o projeto no painel antes de iniciar o app.
- Não há SQLite em produção no Render: o programa recusa essa configuração quando detecta o ambiente Render.
- O plano gratuito não garante disponibilidade para uma operação empresarial contínua.
- O limitador atual pode agrupar usuários atrás do proxy do Render. A configuração de proxies/limites deve ser revisada conforme o uso real.

## Validação do pacote

Testes da API e da normalização PostgreSQL executados localmente em SQLite. Sem credenciais de Supabase, não foi possível executar migrations ou verificar o fluxo contra o PostgreSQL real. O build Docker também precisa ser validado no Render. O pacote não inclui credenciais e não representa um serviço publicado.

## Referências

https://supabase.com/docs/guides/database/connecting-to-postgres
https://render.com/docs/docker
https://render.com/docs/blueprint-spec
