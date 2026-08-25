# Pull Career OS–recommended Ollama models (Windows).
# Usage:
#   .\scripts\install-ollama-models.ps1
#   .\scripts\install-ollama-models.ps1 -Profile light
#   .\scripts\install-ollama-models.ps1 -Profile strong
#   .\scripts\install-ollama-models.ps1 -Profile kimi-cloud

param(
  [ValidateSet("light", "balanced", "strong", "kimi-cloud")]
  [string]$Profile = "balanced"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
  Write-Host "Ollama not found. Install from https://ollama.com then re-run."
  exit 1
}

Write-Host "==> Ollama found"
Write-Host "==> Profile: $Profile"

function Pull-Model([string]$Model) {
  Write-Host ""
  Write-Host "---- pulling $Model ----"
  ollama pull $Model
  if ($LASTEXITCODE -ne 0) { throw "Failed to pull $Model" }
}

$Main = "qwen3:8b"
switch ($Profile) {
  "light" {
    Pull-Model "qwen2.5:3b"
    Pull-Model "nomic-embed-text"
    $Main = "qwen2.5:3b"
  }
  "balanced" {
    Pull-Model "qwen3:8b"
    Pull-Model "deepseek-r1:7b"
    Pull-Model "nomic-embed-text"
    $Main = "qwen3:8b"
  }
  "strong" {
    Pull-Model "qwen3:14b"
    Pull-Model "deepseek-r1:14b"
    Pull-Model "nomic-embed-text"
    $Main = "qwen3:14b"
  }
  "kimi-cloud" {
    Write-Host "Kimi via Ollama Cloud (not local). Run: ollama signin"
    Pull-Model "kimi-k2.6:cloud"
    Pull-Model "nomic-embed-text"
    $Main = "kimi-k2.6:cloud"
  }
}

Write-Host ""
Write-Host "==> Installed models:"
ollama list

Write-Host ""
Write-Host "Set in backend/.env:"
Write-Host "  LLM_PROVIDER=ollama"
Write-Host "  OLLAMA_BASE_URL=http://localhost:11434/v1"
Write-Host "  OLLAMA_MODEL=$Main"
Write-Host "  OLLAMA_NUM_CTX=8192"
Write-Host "  OLLAMA_MAX_TOKENS=800"
Write-Host "  EMBEDDING_MODEL=nomic-embed-text"
Write-Host "  EMBEDDING_DIMS=768"
Write-Host ""
Write-Host "Restart the API, then Canvas → LLM → Ollama."
Write-Host "Docs: docs/install_open_models.md"
