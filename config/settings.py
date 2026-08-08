import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    bot_token: str = Field(default="", description="Telegram Bot Token from @BotFather")
    max_concurrent_downloads: int = Field(default=3, description="Parallel download worker limit")
    max_file_size_mb: int = Field(default=2000, description="Max allowed file size in MB")
    download_dir: str = Field(default="./downloads", description="Temporary directory for downloaded media")
    keep_temp_files: bool = Field(default=False, description="Debug mode: keep temp files after upload")
    ffmpeg_path: str = Field(default="auto", description="FFmpeg binary path or 'auto'")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_download_path(self) -> Path:
        path = Path(self.download_dir).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
