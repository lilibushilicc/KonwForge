from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as api_v1_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.core.response import make_envelope_middleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("%s starting, db=%s", settings.APP_NAME, settings.DB_URL)
    yield
    logger.info("%s stopped", settings.APP_NAME)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="个人在线答题练习网站 · 后端 API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.state.debug = settings.DEBUG
    app.middleware("http")(make_envelope_middleware(settings.API_PREFIX))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_v1_router, prefix=settings.API_PREFIX)

    @app.get("/health", tags=["system"], summary="健康检查")
    def health() -> dict:
        return {"status": "ok", "app": settings.APP_NAME}

    return app


app = create_app()
