# VoltBot ⚡

Busca faturas da Enel por e-mail (IMAP) e envia via Evolution API (WhatsApp),
falando como o VoltBot.

## Configuração

```bash
cp .env.example .env
# edite o .env com os dados reais (IMAP + Evolution)
```

Instalações, contatos e contas de e-mail de origem são gerenciados pela
interface web (SQLite em `DB_PATH`, padrão `data/voltbot.db`).

## Interface web

```bash
uv run voltbot-web
# abre http://127.0.0.1:8000
```

A interface permite: acompanhar status e logs, executar on-demand (dia, data
ou mês inteiro, com dry-run), cadastrar contas de e-mail de origem e gerenciar
instalações e contatos. Sem autenticação — uso local (bind em `WEB_HOST`).

## Evolution API (Docker)

```bash
docker compose up -d evolution-api voltbot-web
# parear a instância via QR code; a interface sobe em http://127.0.0.1:8000
# o worker CLI em loop continua manual:
docker compose --profile app run --rm voltbot --once
```

## Local

```bash
uv sync
# loop contínuo (usa o dia atual a cada ciclo)
uv run voltbot
# rodada única
uv run voltbot --once
```
