# enel-auto

Busca faturas da Enel por e-mail (IMAP) e envia via Evolution API (WhatsApp).

## Configuração

```bash
cp .env.example .env
cp config.example.yaml config.yaml
# edite .env e config.yaml com os dados reais
```

`config.yaml` contém telefones reais e fica fora do git (ver `.gitignore`).

## Evolution API (Docker)

```bash
docker compose up -d evolution-api
# parear a instância via QR code e depois rodar o app:
docker compose --profile app run --rm enel-auto --date 2026-09-13
```

## Local

```bash
uv sync
uv run enel-auto --date 2026-09-13
```
