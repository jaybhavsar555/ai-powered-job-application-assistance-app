#!/usr/bin/env bash
# Pull Career OS–recommended Ollama models.
# Usage: ./scripts/install-ollama-models.sh [light|balanced|strong|kimi-cloud]
set -euo pipefail

PROFILE="${1:-balanced}"

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama not found. Install from https://ollama.com then re-run."
  exit 1
fi

echo "==> Ollama: $(ollama --version 2>/dev/null || echo installed)"
echo "==> Profile: $PROFILE"

pull() {
  local model="$1"
  echo ""
  echo "---- pulling $model ----"
  ollama pull "$model"
}

case "$PROFILE" in
  light)
    # ~8GB RAM / CPU
    pull qwen2.5:3b
    pull nomic-embed-text
    MAIN=qwen2.5:3b
    ;;
  balanced)
    # ~16GB RAM / 8GB VRAM
    pull qwen3:8b
    pull deepseek-r1:7b
    pull nomic-embed-text
    MAIN=qwen3:8b
    ;;
  strong)
    # ~32GB RAM / 12–16GB+ VRAM
    pull qwen3:14b
    pull deepseek-r1:14b
    pull nomic-embed-text
    MAIN=qwen3:14b
    ;;
  kimi-cloud)
    echo "Kimi via Ollama Cloud (not local weights). You must: ollama signin"
    pull kimi-k2.6:cloud
    pull nomic-embed-text
    MAIN=kimi-k2.6:cloud
    ;;
  *)
    echo "Unknown profile: $PROFILE (use light|balanced|strong|kimi-cloud)"
    exit 1
    ;;
esac

echo ""
echo "==> Installed models:"
ollama list

echo ""
echo "Set in backend/.env:"
echo "  LLM_PROVIDER=ollama"
echo "  OLLAMA_BASE_URL=http://localhost:11434/v1"
echo "  OLLAMA_MODEL=$MAIN"
echo "  OLLAMA_NUM_CTX=8192"
echo "  OLLAMA_MAX_TOKENS=800"
echo "  EMBEDDING_MODEL=nomic-embed-text"
echo "  EMBEDDING_DIMS=768"
echo ""
echo "Then restart the API and choose Ollama in Canvas → LLM."
echo "Docs: docs/install_open_models.md"
