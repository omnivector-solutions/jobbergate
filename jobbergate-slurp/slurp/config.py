from typing import Optional

from pydantic import BaseSettings, Field, HttpUrl


class Settings(BaseSettings):
    LEGACY_DATABASE_USER: str
    LEGACY_DATABASE_PSWD: str
    LEGACY_DATABASE_HOST: str
    LEGACY_DATABASE_PORT: int
    LEGACY_DATABASE_NAME: str

    NEXTGEN_DATABASE_USER: str
    NEXTGEN_DATABASE_PSWD: str
    NEXTGEN_DATABASE_HOST: str
    NEXTGEN_DATABASE_PORT: int
    NEXTGEN_DATABASE_NAME: str

    AUTH0_DOMAIN: str
    AUTH0_AUDIENCE: str
    AUTH0_CLIENT_ID: str
    AUTH0_CLIENT_SECRET: str

    class Config:
        env_file = ".env"


settings = Settings()
