"""Outside, Not Online — FastAPI backend."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.challenge_routes import router as challenges_router
from app.api.test_routes import router as test_router
from app.config import get_settings
from app.errors import AppError

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI-powered outdoor discovery journal.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(test_router)
app.include_router(challenges_router)


@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    """Return a user-safe message. Stack traces stay in the logs (SPEC §26)."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
