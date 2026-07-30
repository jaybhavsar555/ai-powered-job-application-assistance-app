from contextlib import asynccontextmanager

from app.infrastructure.checkpoints import ensure_windows_selector_loop_policy

# Must run before uvicorn creates the event loop on Windows (psycopg async)
ensure_windows_selector_loop_policy()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.logger import setup_logging
from app.api.v1.api import api_router

settings = get_settings()
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from app.application.services.auth_seed import bootstrap_auth

        await bootstrap_auth()
    except Exception as exc:
        print(f"[Auth] Startup seed skipped: {exc}")

    try:
        from app.marketplace import load_enabled_plugins

        loaded = load_enabled_plugins()
        if loaded:
            print(f"[Marketplace] Loaded plugins: {', '.join(loaded)}")
    except Exception as exc:
        print(f"[Marketplace] Startup load skipped: {exc}")

    try:
        from app.infrastructure.checkpoints import init_checkpointer, get_active_checkpointer
        from app.workflows.graph import build_graph

        status = await init_checkpointer()
        build_graph(get_active_checkpointer(), backend=status["backend"])
        print(f"[Checkpointer] Graph compiled with backend={status['backend']}")
    except Exception as exc:
        print(f"[Checkpointer] Startup skipped: {exc}")

    yield

    try:
        from app.infrastructure.checkpoints import close_checkpointer

        await close_checkpointer()
    except Exception as exc:
        print(f"[Checkpointer] Shutdown skipped: {exc}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for the Job Application Workflow System",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
