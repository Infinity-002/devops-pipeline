from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "task-system"
    app_env: str = "development"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:5173"
    rq_queue_name: str = "tasks"
    rq_worker_burst: bool = False
    task_processing_delay_seconds: float = 0.0

    @field_validator("cors_origins")
    @classmethod
    def normalize_cors_origins(cls, value: str) -> str:
        return ",".join([item.strip() for item in value.split(",") if item.strip()])

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
