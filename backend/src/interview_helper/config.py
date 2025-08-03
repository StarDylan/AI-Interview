from pathlib import Path
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Server settings
    server_host: str = Field(default="0.0.0.0", alias="SERVER_HOST")
    server_port: int = Field(default=3000, alias="SERVER_PORT")

    # CORS settings
    cors_allow_origins: List[str] = Field(default=[], alias="CORS_ALLOW_ORIGINS")

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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Allow parsing comma-separated lists for CORS origins
        env_list_separator = ","


# Create settings instance
settings = Settings()
