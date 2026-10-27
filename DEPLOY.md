# LogiFlow 2.8.0 — Docker e deploy

## O que está pronto

API e interface usam a mesma imagem. O banco SQLite fica no volume `dados`, montado em `/dados`. A aplicação roda como UID 10001, aplica migrations antes do servidor, cadastra o primeiro administrador quando necessário e não adiciona demonstração. A imagem usa Python 3.12 e um processo Uvicorn. Não execute múltiplas réplicas desta configuração SQLite.

O pacote não contém senhas nem seu banco. O Dockerfile e o Compose foram preparados e os scripts foram testados fora do container; o build e a execução real do container ainda precisam ser validados em uma máquina com Docker.

## 1. Rodar no computador

No Windows, instale e abra Docker Desktop em modo Linux containers. É necessário Docker Compose 2.30 ou superior, por causa do `env_file` em formato `raw`, que preserva senhas contendo `$` e aspas.

Abra o terminal na pasta que contém `Dockerfile` e execute:

```powershell
# Verificar instalação
docker version
docker compose version

# Cadastrar as credenciais iniciais (não substitui um arquivo existente)
python scripts/configurar_docker.py

# Construir e iniciar
docker compose up -d --build

# Verificar situação e logs
docker compose ps
docker compose logs --tail=100 app
```

Acesse http://localhost:8000/interface e use o login/senha definidos no configurador. O primeiro build exige internet para obter a imagem Python e as dependências. O `.bat` continua disponível para rodar SEM Docker; não o execute ao mesmo tempo na mesma porta.

Se você não tiver Python na máquina host, copie `.env.docker.example` para `.env.docker`, preencha as credenciais sem aspas e gere uma chave com `docker run --rm python:3.12-slim python -c "import secrets; print(secrets.token_hex(32))"`. Substitua o valor de `JWT_SECRET_KEY` por essa chave. Não deixe a chave de exemplo.

A porta publicada fica acessível somente pelo próprio computador por padrão. Se a porta 8000 estiver ocupada, no PowerShell: `$env:LOGIFLOW_PORTA="8001"`, depois `docker compose up -d --build`; o endereço passa a ser http://localhost:8001/interface.

O arquivo `.env.docker` contém segredos: não publique nem envie ao GitHub. Ele não entra na imagem. As credenciais iniciais são usadas somente se ainda não existir administrador. Para mudar uma senha já cadastrada, use a interface. Após confirmar o primeiro acesso, remova a linha `LOGIFLOW_ADMIN_SENHA` do arquivo e execute `docker compose up -d --force-recreate`; administradores existentes são preservados.

## 2. Preservar os dados existentes ao migrar

Se você quer manter os pedidos e usuários atuais, faça esta etapa ANTES do primeiro `up` com banco novo. Pare o servidor antigo e faça uma cópia consistente do banco. Na pasta da versão antiga:

```powershell
python -c "import sqlite3; origem=sqlite3.connect('logiflow.db'); destino=sqlite3.connect('backup-migracao.db'); origem.backup(destino); destino.close(); origem.close()"
```

Copie `backup-migracao.db` para a pasta da versão Docker. Mantenha o backup original em outro local. Com `.env.docker` já preenchido e SEM instância Docker anterior contendo dados:

```powershell
docker compose build
docker compose create app
docker compose cp ./backup-migracao.db app:/dados/logiflow.db
docker compose run --rm --user root --entrypoint sh app -c "chown 10001:10001 /dados/logiflow.db && chmod 600 /dados/logiflow.db"
docker compose up -d
```

A correção de proprietário acima é necessária porque `docker compose cp` pode copiar como root; o servidor usa outro usuário. Não copie sobre um volume já utilizado: a restauração precisa ocorrer com a aplicação parada e o banco anterior protegido. Se o banco copiado já tiver administrador, entre com o usuário e senha antigos. O configurador não redefine essa senha.

## 3. Parar, reiniciar e atualizar

```powershell
# Parar sem apagar dados
docker compose down

# Retomar
docker compose up -d

# Após atualizar o código: faça backup antes
docker compose up -d --build
```

O nome do projeto Compose é fixo (`logiflow`) para continuar usando o mesmo volume após mudar a pasta da versão. Isso também significa que este Compose representa uma única instalação por host. Não use `down -v` nem remova o volume: isso apaga o banco. O volume não substitui um backup em outro local.

## 4. Backup

```powershell
docker compose exec app python -m scripts.backup_docker
docker compose cp app:/dados/backups ./backups
```

O script cria snapshots datados com a API de backup do SQLite, incluindo dados ainda no WAL. Guarde os arquivos copiados fora do servidor. Para restaurar: pare o serviço, faça backup do estado atual e importe um snapshot pelo procedimento de migração, cuidando para não manter arquivos WAL/SHM de outro banco junto ao snapshot. Não sobrescreva um banco em uso.

## 5. Publicar na internet — etapa pendente

Falta definir a hospedagem e, se houver, o domínio. Este pacote não provisiona servidores nem cria serviços pagos automaticamente.

Em um servidor com Docker, o mesmo Compose pode ficar atrás de um proxy reverso com HTTPS. Se o proxy roda diretamente no host, pode encaminhar para `127.0.0.1:8000`; se roda em outro container, é preciso configurar uma rede Docker compartilhada e encaminhar para `app:8000`. O domínio precisa apontar para o servidor. A configuração concreta de TLS e rede depende da hospedagem escolhida.

Em plataformas que executam diretamente o Dockerfile, configure `JWT_SECRET_KEY`, `LOGIFLOW_ADMIN_USUARIO`, `LOGIFLOW_ADMIN_NOME`, `LOGIFLOW_ADMIN_SENHA` e um disco persistente montado em `/dados`, com escrita para UID 10001. A imagem aceita `PORT`, usa `DATABASE_URL=sqlite:////dados/logiflow.db` e verifica `/database/status` como healthcheck. Mantenha uma réplica e evite deploy simultâneo de duas versões usando o mesmo SQLite; prefira parar a versão anterior antes de iniciar a nova. Sem disco persistente, esta configuração perde dados na recriação do container.

O servidor está com `--no-proxy-headers`: ele não confia em cabeçalhos encaminhados arbitrários. Atrás de proxy, o limitador atual pode enxergar todos os visitantes pelo IP do proxy e aplicar o limite em conjunto. A confiança no proxy e os limites precisam ser ajustados à rede real no deploy. A API e a interface devem permanecer na mesma origem.

## Referências oficiais

- Volumes: https://docs.docker.com/engine/storage/volumes/
- Compose / serviços e env_file: https://docs.docker.com/reference/compose-file/services/
- Boas práticas de build: https://docs.docker.com/build/building/best-practices/
