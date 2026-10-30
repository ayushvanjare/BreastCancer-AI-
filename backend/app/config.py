import secrets
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "BreastCare AI"
    app_secret_key: str = secrets.token_urlsafe(48)
    database_url: str = "sqlite:///./breastcare.db"
    token_ttl_hours: int = 12
    frontend_origin: str = "http://localhost:5173"
    research_model_python: str | None = None
    histopathology_checkpoint: str | None = None
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

settings = Settings()
