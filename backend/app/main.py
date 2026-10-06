"""Outside, Not Online — FastAPI backend."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.auth_routes import router as auth_router
from app.api.challenge_routes import router as challenges_router
from app.api.discovery_routes import router as discoveries_router
from app.api.photo_routes import router as photos_router
from app.api.test_routes import router as test_router
from app.config import get_settings
from app.db.session import init_db
from app.errors import AppError

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI-powered outdoor discovery journal.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(test_router)
app.include_router(auth_router)
app.include_router(challenges_router)
app.include_router(photos_router)
app.include_router(discoveries_router)

# Uploaded photographs are served from here so the journal can display them.
settings.upload_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_path), name="uploads")


@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    """Return a user-safe message. Stack traces stay in the logs (SPEC §26)."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
