from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "ÔMEGA"
    DATABASE_URL: str = "sqlite:///./omega.db"
    CORS_ORIGINS: str = "http://localhost:5173"

    class Config:
        env_file = ".env"


settings = Settings()