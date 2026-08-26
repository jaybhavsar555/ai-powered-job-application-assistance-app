# Local & open-source models for Career OS

> **Full install walkthrough (Windows + Ollama + Kimi):** see [`install_open_models.md`](./install_open_models.md)  
> Scripts: `scripts/install-ollama-models.ps1` / `scripts/install-ollama-models.sh`

Career OS agents use an OpenAI-compatible client. Switch at runtime via Canvas / `PUT /api/v1/llm/provider`, or set `LLM_PROVIDER` in `backend/.env`.

## Recommended setups

### 1. Fully local — Ollama (privacy, free)

```bash
# Install: https://ollama.com
# Or one-shot: ./scripts/install-ollama-models.sh balanced

ollama pull qwen3:8b            # recommended daily model (16GB RAM)
ollama pull qwen3:14b           # stronger if you have VRAM/RAM
ollama pull deepseek-r1:7b      # reasoning for hard fit scores
ollama pull qwen2.5:3b          # light / CPU-friendly
ollama pull nomic-embed-text    # required for Vault semantic search
```

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen3:8b
OLLAMA_NUM_CTX=8192
OLLAMA_MAX_TOKENS=800
OLLAMA_TIMEOUT_SECONDS=300
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIMS=768
```

Docker Compose already points the API at the `ollama` service when stacked.

### 2. Kimi / DeepSeek without a big GPU — Token Harbor

Full **Kimi K2** weights do **not** fit a normal laptop via `ollama pull`. Use Token Harbor:

```env
LLM_PROVIDER=tokenharbor
TOKENHARBOR_API_KEY=th_...
TOKENHARBOR_MODEL=kimi-k3:free
# Alternatives: deepseek-v4-flash:free
```

### 3. Ollama Cloud Kimi (optional, not offline)

```bash
ollama signin
ollama pull kimi-k2.6:cloud
```

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=kimi-k2.6:cloud
```

## What to use for which step

| Pipeline step | Prefer |
|---------------|--------|
| Scan / scrape (boards) | No LLM (APIs + DDG) |
| Score / evaluate | `qwen3:8b` or `deepseek-r1:7b` or `kimi-k3:free` |
| Tailor resume / cover | `qwen3:8b` / `14b` (`num_ctx` 8k+) |
| Draft email / form answers | Same as tailor |
| Embeddings | `nomic-embed-text` only |

## Verify

```bash
curl -s http://localhost:11434/api/tags
# In app: Canvas → LLM → Ollama + model dropdown
# Presets: GET /api/v1/llm/model-presets
```
