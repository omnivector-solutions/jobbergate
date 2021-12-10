"""
Settings for the Jobbergate Slurp application.
"""

from typing import Optional

from auto_name_enum import AutoNameEnum, NoMangleMixin, auto
from pydantic import BaseSettings


class DatabaseEnv(AutoNameEnum, NoMangleMixin):
    LEGACY = auto()
    NEXTGEN = auto()
    MIRROR = auto()


class Settings(BaseSettings):
    """
    Settings model. Will load from environment and dotenv files.
    """
    LEGACY_DATABASE_USER: str
    LEGACY_DATABASE_PSWD: str
    LEGACY_DATABASE_HOST: str
    LEGACY_DATABASE_PORT: int
    LEGACY_DATABASE_NAME: str

    LEGACY_S3_ENDPOINT_URL: Optional[str]
    LEGACY_S3_BUCKET_NAME: str
    LEGACY_AWS_ACCESS_KEY_ID: str
    LEGACY_AWS_SECRET_ACCESS_KEY: str

    NEXTGEN_DATABASE_USER: str
    NEXTGEN_DATABASE_PSWD: str
    NEXTGEN_DATABASE_HOST: str
    NEXTGEN_DATABASE_PORT: int
    NEXTGEN_DATABASE_NAME: str

    NEXTGEN_S3_ENDPOINT_URL: Optional[str]
    NEXTGEN_S3_BUCKET_NAME: str
    NEXTGEN_AWS_ACCESS_KEY_ID: str
    NEXTGEN_AWS_SECRET_ACCESS_KEY: str

    MIRROR_DATABASE_USER: str
    MIRROR_DATABASE_PSWD: str
    MIRROR_DATABASE_HOST: str
    MIRROR_DATABASE_PORT: int
    MIRROR_DATABASE_NAME: str

    MIRROR_S3_ENDPOINT_URL: Optional[str]
    MIRROR_S3_BUCKET_NAME: str
    MIRROR_AWS_ACCESS_KEY_ID: str
    MIRROR_AWS_SECRET_ACCESS_KEY: str

    AUTH0_DOMAIN: str
    AUTH0_AUDIENCE: str
    AUTH0_CLIENT_ID: str
    AUTH0_CLIENT_SECRET: str

    class Config:
        """
        Special settings for Pydanitc BaseSettings.
        """
        env_file = ".env"


settings = Settings()
