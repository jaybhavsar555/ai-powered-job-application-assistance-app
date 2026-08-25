# Local & open-source models for Career OS

Career OS agents use an OpenAI-compatible client. Switch at runtime via Canvas / `PUT /api/v1/llm/provider`, or set `LLM_PROVIDER` in `backend/.env`.

## Recommended setups

### 1. Fully local — Ollama (privacy, free)

```bash
# Install: https://ollama.com
ollama pull qwen2.5:7b          # good default for agents (8GB+ RAM)
ollama pull qwen2.5:3b          # lighter / CPU-friendly (default in compose)
ollama pull llama3.1:8b         # strong general English
ollama pull deepseek-r1:8b      # reasoning-heavy scoring (slower)
ollama pull nomic-embed-text    # required for Vault semantic search
```

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_NUM_CTX=8192
OLLAMA_MAX_TOKENS=800
OLLAMA_TIMEOUT_SECONDS=300
```

Docker Compose already points the API at the `ollama` service when stacked.

### 2. Kimi / DeepSeek without a big GPU — Token Harbor

Token Harbor is OpenAI-compatible. Free catalog IDs work for structured JSON agents:

```env
LLM_PROVIDER=tokenharbor
TOKENHARBOR_API_KEY=th_...
TOKENHARBOR_MODEL=kimi-k3:free
# Alternatives: deepseek-v4-flash:free
```

Full Kimi K2 weights need multi-GPU hosting — not a laptop Ollama pull. Prefer `kimi-k3:free` via Token Harbor, or Ollama’s **cloud** tags (`kimi-k2.6:cloud`) if you accept remote inference through Ollama Cloud (not offline).

### 3. Ollama Cloud Kimi (optional)

```bash
ollama signin
ollama run kimi-k2.6:cloud
```

Point Career OS at the same Ollama base URL and set `OLLAMA_MODEL=kimi-k2.6:cloud`. This is **not** air-gapped.

## What to use for which step

| Pipeline step | Prefer |
|---------------|--------|
| Scan / scrape (boards) | No LLM (APIs + DDG) |
| Score / evaluate | `qwen2.5:7b` or `kimi-k3:free` |
| Tailor resume / cover | Larger context (`num_ctx` 8k+) |
| Draft email / form answers | Same as tailor |
| Embeddings | `nomic-embed-text` only |

## Verify

```bash
curl -s http://localhost:11434/api/tags
# In app: Canvas → LLM switch → Ollama, or GET /api/v1/llm/provider
# Presets: GET /api/v1/llm/model-presets
```
