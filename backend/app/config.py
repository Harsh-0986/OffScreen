"""Application settings, loaded from environment variables / .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Runtime configuration.

    The Gemini API key is server-side only and must never reach the browser.
    """

    model_config = SettingsConfigDict(
        # Accept the env file at the repo root or inside backend/, whichever exists.
        env_file=(BACKEND_DIR.parent / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Outside, Not Online"
    app_env: str = "development"

    # AI
    gemini_api_key: str | None = None
    gemma_model: str = "gemma-4-26b-a4b-it"

    # Storage / DB
    database_url: str = "sqlite:///./outside.db"
    upload_dir: str = "uploads"
    max_image_bytes: int = 10 * 1024 * 1024

    # Auth. Generate with: python -c "import secrets; print(secrets.token_urlsafe(48))"
    secret_key: str = "dev-only-insecure-secret-change-me"

    # CORS. Kept as a raw string because dotenv values are not JSON-decoded;
    # use `cors_origin_list` for the parsed list.
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        if not path.is_absolute():
            path = BACKEND_DIR / path
        return path

    @property
    def database_path(self) -> Path:
        """Resolve a sqlite file URL to an absolute path."""
        prefix = "sqlite:///"
        if self.database_url.startswith(prefix):
            raw = self.database_url[len(prefix) :]
            if raw == ":memory:":
                return BACKEND_DIR / ":memory:"
            p = Path(raw)
            if not p.is_absolute():
                p = BACKEND_DIR / p
            return p
        return Path(self.database_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
