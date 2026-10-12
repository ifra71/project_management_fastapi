from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Project Management API"
    app_version: str = "1.0.0"

    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "project_management"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()