"""Application configuration with environment variable support."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class RunMode(StrEnum):
    """Application run mode."""

    DEMO = "demo"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings can be overridden via environment variables
    prefixed with ``BINANCE_KYC_``.

    Example::

        export BINANCE_KYC_MODE=production
        export BINANCE_KYC_API_KEY=your_key
        export BINANCE_KYC_TELEGRAM_TOKEN=your_token
    """

    model_config = {"env_prefix": "BINANCE_KYC_"}

    # --- General -----------------------------------------------------------
    mode: RunMode = Field(default=RunMode.DEMO, description="Run mode: demo or production")
    data_dir: Path = Field(default=Path("data"), description="Directory for session data")
    log_level: str = Field(default="INFO", description="Logging level")
    default_language: str = Field(default="en", description="Default language code")
    session_timeout_minutes: int = Field(default=30, description="Session inactivity timeout")

    # --- Telegram ----------------------------------------------------------
    telegram_token: str = Field(default="", description="Telegram bot token")
    telegram_webhook_url: str = Field(default="", description="Webhook URL (optional)")

    # --- Binance API (production only) -------------------------------------
    api_key: str = Field(default="", description="Binance API key")
    api_secret: str = Field(default="", description="Binance API secret")
    api_base_url: str = Field(
        default="https://api.binance.com",
        description="Binance API base URL",
    )

    # --- Image validation --------------------------------------------------
    max_image_size_mb: int = Field(default=10, description="Max image upload size in MB")
    min_image_size_kb: int = Field(default=100, description="Min image upload size in KB")
    allowed_image_types: list[str] = Field(
        default=["image/jpeg", "image/png", "image/webp"],
        description="Allowed MIME types for document images",
    )

    @property
    def sessions_dir(self) -> Path:
        """Directory for session JSON files."""
        return self.data_dir / "sessions"

    @property
    def uploads_dir(self) -> Path:
        """Directory for uploaded images."""
        return self.data_dir / "uploads"

    def ensure_dirs(self) -> None:
        """Create required directories if they don't exist."""
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    """Load settings from environment, with ``.env`` file support."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    return Settings()
