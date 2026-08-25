# Install open-source models for Career OS (Ollama + Kimi)

You already have **Ollama**. Career OS talks to it at `http://localhost:11434/v1`.  
Pull stronger open models, point `.env` at them, and switch in **Canvas → LLM**.

> **Honest note on “better than OpenAI / Claude”**  
> Full frontier models (Claude Opus, GPT-5 class, **Kimi K2 1T**) need cloud or multi-GPU.  
> On a normal PC/laptop, the best open options are **Qwen3**, **DeepSeek-R1 distill**, and **Llama 3.1/3.3**.  
> For **Kimi-class** quality without a datacenter: use **Token Harbor `kimi-k3:free`** or **Ollama Cloud `kimi-k2.6:cloud`** (not offline).

---

## Step 0 — Confirm Ollama is running

**Windows (PowerShell):**

```powershell
ollama --version
ollama list
```

If the app is not running, open **Ollama** from the Start menu, or:

```powershell
ollama serve
```

---

## Step 1 — Pick models by your RAM / VRAM

| Your machine | Pull these (recommended) | Disk ~ |
|--------------|--------------------------|--------|
| **8 GB RAM** (CPU / light GPU) | `qwen2.5:3b` or `qwen3:4b` + `nomic-embed-text` | ~4 GB |
| **16 GB RAM** / **8 GB VRAM** | `qwen3:8b` + `deepseek-r1:7b` + `nomic-embed-text` | ~12 GB |
| **32 GB RAM** / **12–16 GB VRAM** | `qwen3:14b` + `deepseek-r1:14b` + `nomic-embed-text` | ~20 GB |
| **24 GB+ VRAM** | `qwen3-coder:30b` or `qwen3.6:27b` + `deepseek-r1:32b` | ~40 GB |

**Career OS daily flow (score / tailor / email drafts):** prefer **Qwen3 8B+**.  
**Hard fit reasoning:** add **DeepSeek-R1** distill.  
**Vault semantic search:** always pull **`nomic-embed-text`**.

---

## Step 2 — Install with one script

From the repo root:

**Windows PowerShell:**

```powershell
.\scripts\install-ollama-models.ps1
# or lighter / heavier:
.\scripts\install-ollama-models.ps1 -Profile light
.\scripts\install-ollama-models.ps1 -Profile strong
```

**macOS / Linux:**

```bash
chmod +x scripts/install-ollama-models.sh
./scripts/install-ollama-models.sh          # default = balanced
./scripts/install-ollama-models.sh light
./scripts/install-ollama-models.sh strong
```

Or pull manually:

```bash
# Balanced (most people)
ollama pull qwen3:8b
ollama pull deepseek-r1:7b
ollama pull nomic-embed-text

# Stronger (16GB+ VRAM / 32GB RAM)
ollama pull qwen3:14b
ollama pull deepseek-r1:14b
ollama pull nomic-embed-text
```

Verify:

```bash
ollama list
curl http://localhost:11434/api/tags
```

---

## Step 3 — Point Career OS at Ollama

In `backend/.env`:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=qwen3:8b
OLLAMA_NUM_CTX=8192
OLLAMA_MAX_TOKENS=800
OLLAMA_TIMEOUT_SECONDS=300

# Vault embeddings (local)
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIMS=768
```

Docker Compose: use `OLLAMA_BASE_URL=http://ollama:11434/v1` and the same model name.

Restart the API, then in the app: **Canvas → LLM → Ollama**.  
You can also pick a preset model from the switcher (Qwen / DeepSeek / Kimi paths).

---

## How to get **Kimi** (3 options)

### A) Best for Career OS agents — Token Harbor (recommended)

No big download. Free catalog id:

1. Create a key at [tokenharbor.ai](https://tokenharbor.ai/dashboard/api-keys)
2. In `backend/.env`:

```env
LLM_PROVIDER=tokenharbor
TOKENHARBOR_API_KEY=th_your_key
TOKENHARBOR_MODEL=kimi-k3:free
# or: deepseek-v4-flash:free
```

3. Canvas → **Token Harbor**

### B) Ollama Cloud Kimi (uses Ollama CLI, inference is remote)

```bash
ollama signin
ollama pull kimi-k2.6:cloud
# or: ollama run kimi-k2.6:cloud
```

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=kimi-k2.6:cloud
```

This is **not** fully local — prompts leave your machine.

### C) Full Kimi K2 weights on your hardware

Needs **multi-GPU / ~250GB+** memory. Not practical on a laptop.  
Use Hugging Face `moonshotai/Kimi-K2*` + vLLM/SGLang on a server if you need air-gapped K2.

---

## Models that compete well for *this* app

| Goal | Open model | Why |
|------|------------|-----|
| Tailor + JSON agents | `qwen3:8b` / `14b` | Strong structured output, multilingual |
| Score / hard reasoning | `deepseek-r1:7b` / `14b` | Chain-of-thought fit judgments |
| Coding / LaTeX help | `qwen3-coder:30b` (24GB+) | Agentic coding |
| Embeddings | `nomic-embed-text` | Vault search |
| Kimi-like without GPU farm | `kimi-k3:free` (Token Harbor) | Closest easy Kimi path |

Nothing you pull on a 8–16GB laptop will reliably beat Claude Opus / GPT-5 on every task — but **Qwen3 + DeepSeek-R1** are among the strongest *local* open stacks, and **Kimi via Token Harbor / Ollama Cloud** is the practical Kimi path for Career OS.

---

## Quick test

```bash
ollama run qwen3:8b "Return JSON: {\"ok\": true, \"role\": \"backend engineer\"}"
```

Then open Career OS → **Pipeline** or **Discovery** and run a scan with Canvas set to Ollama.
