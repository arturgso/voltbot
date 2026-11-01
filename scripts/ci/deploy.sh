#!/usr/bin/env bash
set -euo pipefail

# A configuração e os dados ficam fora do checkout descartável do runner.
deploy_dir="${VOLTBOT_DEPLOY_DIR:?Informe o diretório da instalação local}"
test -f "$deploy_dir/.env"
test -f "$deploy_dir/docker-compose.yml"
docker info >/dev/null

image="voltbot-local:${GITHUB_SHA:-$(git rev-parse HEAD)}"
docker build --tag "$image" .
override="$(mktemp)"
trap 'rm -f "$override"' EXIT
printf 'services:\n  voltbot-web:\n    image: %s\n' "$image" > "$override"

# Mantém o projeto Compose, seus volumes e os bind mounts originais.
# Não inicia worker nem recria Evolution/PostgreSQL/Redis.
docker compose --project-directory "$deploy_dir" \
  -f "$deploy_dir/docker-compose.yml" -f "$override" \
  up -d --no-deps --no-build voltbot-web

container_id="$(docker compose --project-directory "$deploy_dir" \
  -f "$deploy_dir/docker-compose.yml" -f "$override" ps -q voltbot-web)"
for attempt in {1..30}; do
  if docker exec "$container_id" python -c \
    'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2).close()' 2>/dev/null; then
    echo 'Servidor web atualizado e saudável.'
    exit 0
  fi
  sleep 2
done
echo 'O servidor web não respondeu ao healthcheck após o deploy.' >&2
exit 1
