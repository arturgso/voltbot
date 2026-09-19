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
# loop contínuo (padrão: 1 ciclo a cada 1h)
docker compose --profile app run --rm enel-auto
# rodada única
docker compose --profile app run --rm enel-auto --once
# dia específico + rodada única
docker compose --profile app run --rm enel-auto --date 2026-09-13 --once
```

O intervalo sai de `POLL_INTERVAL_SECONDS` no `.env` (padrão 3600).

## Local

```bash
uv sync
# loop contínuo (usa o dia atual a cada ciclo)
uv run enel-auto
# rodada única
uv run enel-auto --once
```
