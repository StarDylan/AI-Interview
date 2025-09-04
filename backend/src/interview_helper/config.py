from pydantic_settings.main import SettingsConfigDict
from typing import Annotated
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Server settings
    server_host: str = Field(default="0.0.0.0", alias="SERVER_HOST")
    server_port: int = Field(default=3000, alias="SERVER_PORT")

    # CORS settings
    cors_allow_origins: Annotated[list[str], NoDecode] = Field(
        default=[], alias="CORS_ALLOW_ORIGINS"
    )

    # Google OIDC settings
    google_client_id: str = Field(alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(alias="GOOGLE_CLIENT_SECRET")
    site_url: str = Field(default="http://localhost:3000", alias="SITE_URL")
    frontend_redirect_uri: str = Field(default="http://localhost:5173/auth/callback", alias="FRONTEND_REDIRECT_URI")

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def split_origins(cls, v):
        if isinstance(v, str):
            origins = [origin.strip() for origin in v.strip("[]").split(",")]
            # Remove empty strings
            origins = [origin for origin in origins if origin]
            return origins
        return v

    def model_post_init(self, __context):
        if not self.cors_allow_origins:
            raise ValueError(
                "Missing required environment variable: CORS_ALLOW_ORIGINS"
            )

    # Audio processing settings (these rarely change, so keeping as constants is fine)
    num_channels: int = 1
    sample_width: int = 2
    target_sample_rate: int = 48000
    min_duration: int = 5
    bytes_per_sample: int = 2

    # File paths
    vosk_model_path: Path = Field(
        default=Path("vosk_models") / "vosk-model-small-en-us-0.15"
    )
    audio_recordings_dir: str = "audio_recordings"
    transcriptions_dir: str = "transcriptions"

    @property
    def min_bytes(self) -> int:
        """Derived setting for minimum bytes"""
        return int(self.target_sample_rate * self.bytes_per_sample * self.min_duration)

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", frozen=True
    )
