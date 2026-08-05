from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.db import engine
from api.routers import collection, profile, progress, universes


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title="Universe Anime Planet API", lifespan=lifespan)

# В проде Caddy проксирует и фронтенд, и /api под одним доменом (см. Caddyfile) —
# same-origin, CORS не нужен вовсе. Разрешаем всё только для локальной разработки API
# отдельно от Caddy (например, `vite dev` на другом порту).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["X-Telegram-Init-Data"],
)

app.include_router(profile.router)
app.include_router(universes.router)
app.include_router(collection.router)
app.include_router(progress.router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
