"""
Configuration file, sets all the necessary environment variables, it is better used with a .env file
"""
from pydantic import BaseSettings, Field

_DB_RX = r"^(sqlite|postgres)://.+$"


class Settings(BaseSettings):
    DATABASE_URL: str = Field("sqlite:///./sqlite.db?check_same_thread=true", regex=_DB_RX)
    TEST_ENV: bool = Field(False)
    SECRET_KEY: str
    TOKEN_URL: str = Field("token/")
    ALGORITHM: str = Field("HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field("30")
    SERVERLESS_STAGE: str = Field("staging")
    SERVERLESS_REGION: str = Field("eu-north-1")
    S3_BASE_PATH: str = Field("jobbergate-resources")
    # BACKEND_CORS_ORIGINS example: "['https://example1.com', 'https://example2.com']"
    BACKEND_CORS_ORIGINS: str = Field("[]")

    class Config:
        env_file = ".env"


settings = Settings()
