# Production deploy (Career OS)

## Quick start

```bash
cp .env.production.example .env.production
# Edit POSTGRES_PASSWORD, REDIS_PASSWORD, SECRET_KEY

docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build

# Pull chat + embed models inside the ollama service
docker compose -f docker-compose.prod.yml exec ollama ollama pull qwen2.5:3b
docker compose -f docker-compose.prod.yml exec ollama ollama pull nomic-embed-text
```

- API: `http://localhost:8001` (or `API_PORT`)
- Web: `http://localhost:3000` (or `WEB_PORT`)
- Register at `/login` or use **Continue as demo**

## Secrets checklist

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | JWT signing |
| `POSTGRES_PASSWORD` | Postgres |
| `REDIS_PASSWORD` | Redis auth |
| `OPENAI_API_KEY` | Optional cloud LLM |
| `NEXT_PUBLIC_API_URL` | Browser → API base (baked at Next build) |

Do **not** commit `.env.production`.

## Local vs prod compose

| File | Use |
|------|-----|
| `docker-compose.yml` | Dev infra only (db/redis/qdrant/ollama); run API/UI on host |
| `docker-compose.prod.yml` | Full stack including `api` + `web` images |

## Auth

- `POST /api/v1/auth/register` / `login` — real email/password  
- `POST /api/v1/auth/demo` — still available for local smoke tests  

## Checkpoints

- LangGraph `MemorySaver` keyed by `job_id`  
- `GET /api/v1/workflows/{job_id}/checkpoint`  
- SSE `?resume=true` or Canvas **Resume checkpoint**  

## Marketplace

- Plugin YAML under `backend/app/marketplace/plugins/`  
- UI: `/marketplace` · API: `/api/v1/marketplace/plugins`
