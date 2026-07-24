from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_env: str = "development"
    app_name: str = "Totem API"
    api_v1_prefix: str = "/api/v1"
    secret_key: str = "development-only"
    database_url: str = "sqlite:///./data/app.db"
    cors_origins: str = "http://localhost:5173"
    openai_api_key: str = ""
    openai_api_key_parameter_name: str = ""
    aws_region: str = ""
    openai_image_model: str = "gpt-image-1"
    openai_prompt_compiler_model: str = "gpt-5-mini"
    use_prompt_compiler: bool = True
    generation_hourly_limit: int = 100
    generation_daily_limit: int = 300
    generation_stale_minutes: int = 10
    image_storage_root: str = "backend/data/images"
    image_max_bytes: int = 20_000_000
    image_max_dimension: int = 8192
    image_max_pixels: int = 40_000_000
    image_min_free_bytes: int = 2 * 1024 * 1024 * 1024
    image_min_free_percent: float = 20.0
    data_retention_minutes: int = 14 * 24 * 60
    session_cookie_name: str = "totem_session"
    session_ttl_minutes: int = 8 * 60
    session_cookie_secure: bool = False
    login_failure_limit: int = 5
    login_failure_window_minutes: int = 15

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
