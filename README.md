# enel-auto

Busca faturas da Enel por e-mail (IMAP) e envia via Evolution API (WhatsApp).

## Configuração

```bash
cp .env.example .env
# edite o .env com os dados reais (IMAP + Evolution)
```

Instalações, contatos e contas de e-mail de origem são gerenciados pela
interface web (SQLite em `DB_PATH`, padrão `data/enel_auto.db`).

## Interface web

```bash
uv run enel-auto-web
# abre http://127.0.0.1:8000
```

A interface permite: acompanhar status e logs, executar on-demand (dia, data
ou mês inteiro, com dry-run), cadastrar contas de e-mail de origem e gerenciar
instalações e contatos. Sem autenticação — uso local (bind em `WEB_HOST`).

## Evolution API (Docker)

```bash
docker compose up -d evolution-api enel-auto-web
# parear a instância via QR code; a interface sobe em http://127.0.0.1:8000
# o worker CLI em loop continua manual:
docker compose --profile app run --rm enel-auto --once
```

## Local

```bash
uv sync
# loop contínuo (usa o dia atual a cada ciclo)
uv run enel-auto
# rodada única
uv run enel-auto --once
```
