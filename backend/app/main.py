"""FastAPI entrypoint."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, chat, conversations, dashboard, documents, evaluation, search
from app.config import get_settings
from app.core.logging import setup_logging
from app.models.database import init_db

settings = get_settings()
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()  # create tables if missing
    logger.info("database_ready url_scheme=%s", settings.database_url.split(":")[0])
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.12.0",
    description="Production-grade RAG document assistant API.",
    lifespan=lifespan,
)

allowed_origins = [
    "https://rag-document-assistant-frontend-7ksx.onrender.com",
    "http://localhost:3000",
]
for origin in settings.cors_origin_list:
    if origin not in allowed_origins:
        allowed_origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(conversations.router)
app.include_router(search.router)
app.include_router(chat.router)
app.include_router(dashboard.router)
app.include_router(evaluation.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Log details server-side; return a generic message to the client.
    logger.exception("unhandled_error path=%s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


@app.get("/api/health", tags=["system"])
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "llm_provider": settings.llm_provider,
    }
