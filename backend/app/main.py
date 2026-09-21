import logging
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from backend.app.config import settings
from backend.app.schemas.health import HealthResponse, PublicConfigResponse, ProviderStatus
from backend.app.db.session import init_db, async_session_factory
from backend.app.routers.sessions import router as sessions_router

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("lenny-growth-assistant")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing The Lenny Growth Assistant backend service...")
    logger.info("Environment: %s | App Version: %s", settings.ENVIRONMENT, settings.APP_VERSION)
    logger.info("Database URL: %s", settings.DATABASE_URL)
    logger.info("CORS Allowed Origins: %s", settings.cors_origin_list)
    logger.info("Ollama Base URL: %s | Model: %s", settings.OLLAMA_BASE_URL, settings.OLLAMA_MODEL)
    logger.info("Cloud LLMs configured: Gemini=%s, OpenRouter=%s", settings.has_gemini, settings.has_openrouter)

    # Initialize database schema tables
    try:
        await init_db()
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.error("Database schema initialization failed: %s", e)
        raise

    yield
    logger.info("Shutting down The Lenny Growth Assistant backend service.")


app = FastAPI(
    title="The Lenny Growth Assistant API",
    description="Grounded AI assistant for product & startup growth frameworks from Lenny's Podcast.",
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS configuration for client browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sessions_router)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request, exc: HTTPException):
    """
    Standardizes error responses to { "error": { "code": ..., "message": ... } }
    """
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail}
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail)
            }
        }
    )


@app.get("/", summary="Root index")
async def root():
    return {
        "service": "The Lenny Growth Assistant API",
        "version": settings.APP_VERSION,
        "docs_url": "/docs",
        "health_url": "/health"
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Active readiness & liveness probe",
    description="Truthfully probes DB connectivity and local Ollama daemon reachability."
)
async def health_check():
    # 1. Probe Ollama daemon asynchronously with a short 1.5s timeout
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                ollama_ok = True
    except Exception as e:
        logger.debug("Ollama health check probe failed: %s", e)
        ollama_ok = False

    # 2. Probe Database connectivity by executing a live SELECT 1
    db_ok = False
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception as e:
        logger.error("Database health check probe failed: %s", e)
        db_ok = False

    # Determine composite status
    is_healthy = db_ok and (ollama_ok or settings.cloud_llm_configured)
    status_label = "healthy" if is_healthy else "degraded"

    return HealthResponse(
        status=status_label,
        db=db_ok,
        ollama=ollama_ok,
        cloud_llm_configured=settings.cloud_llm_configured,
        version=settings.APP_VERSION
    )



@app.get(
    "/config",
    response_model=PublicConfigResponse,
    summary="Public runtime configuration",
    description="Exposes safe model router mappings and availability without exposing secrets."
)
async def public_config():
    return PublicConfigResponse(
        environment=settings.ENVIRONMENT,
        version=settings.APP_VERSION,
        cloud_llm_configured=settings.cloud_llm_configured,
        providers={
            "ollama": ProviderStatus(
                configured=True,
                default_model=settings.OLLAMA_MODEL
            ),
            "gemini": ProviderStatus(
                configured=settings.has_gemini,
                default_model=settings.GEMINI_MODEL
            ),
            "openrouter": ProviderStatus(
                configured=settings.has_openrouter,
                default_model=settings.OPENROUTER_MODEL
            )
        },
        task_routing={
            "intent_routing": settings.MODEL_FOR_INTENT,
            "retrieval_qa": settings.MODEL_FOR_RETRIEVAL_QA,
            "essay_generation": settings.MODEL_FOR_ESSAY,
            "artifact_generation": settings.MODEL_FOR_ARTIFACT
        },
        cors_origins=settings.cors_origin_list
    )
