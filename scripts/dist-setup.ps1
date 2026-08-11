# Career OS — one-shot installer for end users (Windows PowerShell).
# Runs the full stack on THIS machine. Does not contact the author's PC.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

function Require-Docker {
  if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker not found. Install Docker Desktop:"
    Write-Host "  https://docs.docker.com/desktop/setup/install/windows-install/"
    exit 1
  }
  docker compose version | Out-Null
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker Compose plugin missing."
    exit 1
  }
}

Require-Docker

if (-not (Test-Path ".env.dist")) {
  Copy-Item ".env.dist.example" ".env.dist"
  Write-Host "Created .env.dist — edit SECRET_KEY, POSTGRES_PASSWORD, REDIS_PASSWORD, then re-run."
  Write-Host "  notepad .env.dist"
  exit 1
}

$envText = Get-Content ".env.dist" -Raw
if ($envText -match "change-me-strong|replace-with-a-long-random") {
  Write-Host "Update placeholder secrets in .env.dist before starting."
  exit 1
}

New-Item -ItemType Directory -Force -Path "data\resumes", "data\packages" | Out-Null

$compose = @("compose", "-f", "docker-compose.dist.yml", "--env-file", ".env.dist")

Write-Host "==> Pulling / building images…"
docker @compose pull 2>$null
docker @compose up -d --build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> Waiting for Ollama…"
for ($i = 0; $i -lt 60; $i++) {
  docker @compose exec -T ollama ollama list 2>$null | Out-Null
  if ($LASTEXITCODE -eq 0) { break }
  Start-Sleep -Seconds 2
}

function Get-DotEnvValue([string]$key, [string]$default) {
  $line = Get-Content ".env.dist" | Where-Object { $_ -match "^\s*$key\s*=" } | Select-Object -First 1
  if (-not $line) { return $default }
  return ($line -split "=", 2)[1].Trim()
}

$chat = Get-DotEnvValue "OLLAMA_MODEL" "qwen2.5:3b"
$embed = Get-DotEnvValue "EMBEDDING_MODEL" "nomic-embed-text"
$apiPort = Get-DotEnvValue "API_PORT" "8001"
$webPort = Get-DotEnvValue "WEB_PORT" "3000"

Write-Host "==> Pulling chat model: $chat (not baked into the image)…"
docker @compose exec -T ollama ollama pull $chat
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> Pulling embedding model: $embed…"
docker @compose exec -T ollama ollama pull $embed
if ($LASTEXITCODE -ne 0) {
  Write-Host "Warning: embed pull failed — Vault semantic search may be limited."
}

Write-Host ""
Write-Host "Career OS is up on this computer:"
Write-Host "  UI:  http://localhost:$webPort"
Write-Host "  API: http://localhost:$apiPort/docs"
Write-Host "Register an account at /login."
Write-Host ""
Write-Host "Stop later:  docker compose -f docker-compose.dist.yml --env-file .env.dist down"
