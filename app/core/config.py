from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ai-agent"
    app_host: str = "0.0.0.0"
    app_port: int = 8001
    backend_base_url: str = Field(default="http://backend:8000", alias="BACKEND_BASE_URL")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    model_name: str = Field(default="gemini-2.5-flash", alias="MODEL_NAME")
    request_timeout_seconds: float = 15.0


settings = Settings()
