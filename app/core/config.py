from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Satellite Imagery Gateway"
    version: str = "1.0.0"
    description: str = (
        "API unificada para consultar, descargar y procesar imágenes satelitales"
    )

    # Database
    database_url: str = "sqlite:///./satellite_imagery.db"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # JWT
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # API
    api_v1_prefix: str = "/api/v1"

    # Environment
    environment: str = "development"
    debug: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
