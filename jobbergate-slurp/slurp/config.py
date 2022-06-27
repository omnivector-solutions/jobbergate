"""
Settings for the Jobbergate Slurp application.
"""

from typing import Optional

from pydantic import BaseSettings


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

    class Config:
        """
        Special settings for Pydantic BaseSettings.
        """

        env_file = ".env"


settings = Settings()
