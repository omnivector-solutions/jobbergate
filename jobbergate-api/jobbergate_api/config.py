"""
Configuration file, sets all the necessary environment variables, it is better used with a .env file
"""
from enum import Enum
from typing import Optional

from pydantic import BaseSettings, Field, HttpUrl


class LogLevelEnum(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DeployEnvEnum(str, Enum):
    """
    Describes the environment where the app is currently deployed.
    """

    PROD = "PROD"
    STAGING = "STAGING"
    LOCAL = "LOCAL"
    TEST = "TEST"


class Settings(BaseSettings):

    DEPLOY_ENV: Optional[DeployEnvEnum] = DeployEnvEnum.LOCAL

    LOG_LEVEL: LogLevelEnum = LogLevelEnum.INFO

    # Database settings  # Default to values from docker-compose.yml
    DATABASE_HOST: Optional[str] = "db"
    DATABASE_USER: Optional[str] = "jobbergate"
    DATABASE_PSWD: Optional[str] = "local-pswd"
    DATABASE_NAME: Optional[str] = "jobbergate"
    DATABASE_PORT: Optional[int] = 5432

    # Test database settings
    TEST_DATABASE_HOST: Optional[str] = "localhost"
    TEST_DATABASE_USER: Optional[str] = "test"
    TEST_DATABASE_PSWD: Optional[str] = "test-pswd"
    TEST_DATABASE_NAME: Optional[str] = "test-jobbergate"
    TEST_DATABASE_PORT: Optional[int] = 5433

    # S3 configuration
    S3_BUCKET_NAME: str = Field("jobbergate-staging-eu-north-1-resources")
    S3_ENDPOINT_URL: Optional[str]
    AWS_ACCESS_KEY_ID: Optional[str]
    AWS_SECRET_ACCESS_KEY: Optional[str]

    # Security Settings. For details, see https://github.com/omnivector-solutions/armsec
    ARMASEC_DOMAIN: str
    ARMASEC_AUDIENCE: Optional[HttpUrl]
    ARMASEC_DEBUG: bool = Field(False)

    # Key to custom claims packaged with Auth0 tokens
    IDENTITY_CLAIMS_KEY: str = "https://omnivector.solutions"

    # Sentry configuration
    SENTRY_DSN: Optional[HttpUrl]
    SENTRY_SAMPLE_RATE: Optional[float] = Field(1.0, gt=0.0, le=1.0)

    # Maximum number of bytes allowed for file uploads
    MAX_UPLOAD_FILE_SIZE: int = 100 * 1024 * 1024  # 100 MB

    class Config:
        env_file = ".env"


settings = Settings()
