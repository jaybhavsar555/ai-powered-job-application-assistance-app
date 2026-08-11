#!/usr/bin/env bash
# Career OS — one-shot installer for end users (macOS / Linux).
# Runs the full stack on THIS machine. Does not contact the author's PC.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE=(docker compose -f docker-compose.dist.yml --env-file .env.dist)

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker not found. Install Docker Desktop or Engine:"
  echo "  https://www.docker.com/products/docker-desktop/"
  echo "  https://docs.docker.com/engine/install/"
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose plugin missing: https://docs.docker.com/compose/install/"
  exit 1
fi

if [[ ! -f .env.dist ]]; then
  cp .env.dist.example .env.dist
  echo "Created .env.dist — edit SECRET_KEY, POSTGRES_PASSWORD, REDIS_PASSWORD, then re-run."
  echo "  nano .env.dist   # or your editor"
  exit 1
fi

# Fail early if example secrets left unchanged
if grep -q 'change-me-strong\|replace-with-a-long-random' .env.dist; then
  echo "Update placeholder secrets in .env.dist before starting."
  exit 1
fi

mkdir -p data/resumes data/packages

echo "==> Pulling / building images…"
# Prefer pull when API_IMAGE/WEB_IMAGE are set; always allow local build fallback
"${COMPOSE[@]}" pull || true
"${COMPOSE[@]}" up -d --build

# Wait for Ollama API
echo "==> Waiting for Ollama…"
for i in $(seq 1 60); do
  if docker compose -f docker-compose.dist.yml --env-file .env.dist exec -T ollama \
    ollama list >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

# shellcheck disable=SC1091
set -a
# shellcheck source=/dev/null
source .env.dist
set +a
CHAT_MODEL="${OLLAMA_MODEL:-qwen2.5:3b}"
EMBED_MODEL="${EMBEDDING_MODEL:-nomic-embed-text}"

echo "==> Pulling chat model: ${CHAT_MODEL} (not baked into the image)…"
"${COMPOSE[@]}" exec -T ollama ollama pull "${CHAT_MODEL}"

echo "==> Pulling embedding model: ${EMBED_MODEL}…"
"${COMPOSE[@]}" exec -T ollama ollama pull "${EMBED_MODEL}" || \
  echo "Warning: embed pull failed — Vault semantic search may be limited."

API_PORT="${API_PORT:-8001}"
WEB_PORT="${WEB_PORT:-3000}"

echo ""
echo "Career OS is up on this computer:"
echo "  UI:  http://localhost:${WEB_PORT}"
echo "  API: http://localhost:${API_PORT}/docs"
echo "Register an account at /login — do not reuse someone else's credentials."
echo ""
echo "Stop later:  docker compose -f docker-compose.dist.yml --env-file .env.dist down"
