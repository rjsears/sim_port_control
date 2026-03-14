# =============================================================================
# SimPortControl Configuration
# =============================================================================
"""
Application configuration using Pydantic Settings.
All settings can be overridden via environment variables.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "SimPortControl"
    app_env: Literal["development", "production", "testing"] = "production"
    debug: bool = False
    domain: str = "simportcontrol.loft.aero"
    timezone: str = "America/Chicago"

    # Security
    secret_key: str  # Required - JWT signing key
    encryption_key: str  # Required - Fernet key for credential encryption
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"

    # Database
    database_host: str = "db"
    database_port: int = 5432
    database_name: str = "simportcontrol"
    database_user: str = "simportcontrol"
    database_password: str  # Required

    # Default Settings
    default_timeout_hours: int = 4
    default_vlan: int = 30

    # Admin User (created on first run)
    admin_username: str = "admin"
    admin_password: str = "changeme"  # Should be changed on setup

    # Logging
    log_level: str = "INFO"

    @property
    def database_url(self) -> str:
        """Construct async database URL."""
        return (
            f"postgresql+asyncpg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def sync_database_url(self) -> str:
        """Construct sync database URL for Alembic."""
        return (
            f"postgresql://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
