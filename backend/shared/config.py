from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Look for .env in the current working directory first, then one level up
        # (supports running uvicorn from backend/ OR from the project root).
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: str = "development"
    log_level: str = "INFO"
    debug: bool = False

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "wildtrack"
    postgres_user: str = "wildtrack"
    postgres_password: str = "wildtrack"

    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "wildtrack"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "wildtrack-media"
    minio_use_ssl: bool = False
    minio_presigned_url_expiry: int = 900

    # MQTT
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_client_id: str = "wildtrack-backend"

    # Security
    jwt_secret_key: str = "change-me-in-production"
    jwt_expiry_seconds: int = 86400

    # Admin bootstrap (used by seed script in Slice 1)
    admin_seed_email: str = "admin@wildtrack.local"
    admin_seed_password: str = "ChangeThisImmediately!"


@lru_cache
def get_settings() -> Settings:
    return Settings()
