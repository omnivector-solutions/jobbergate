"""
Configuration file, sets all the necessary environment variables, it is better used with a .env file
"""
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    DATABASE_URL: str
    TEST_DATABASE_URL: str
    TEST_ENV: bool = Field(False)
    SECRET_KEY: str
    TOKEN_URL: str = Field("token")
    ALGORITHM: str = Field("HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field("30")

    class Config:
        env_file = ".env"


settings = Settings()
