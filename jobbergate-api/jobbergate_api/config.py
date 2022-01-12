"""
Configuration file, sets all the necessary environment variables, it is better used with a .env file
"""
from enum import Enum
from typing import Optional

from pydantic import BaseSettings, Field, HttpUrl, root_validator
from yarl import URL


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


class Settings(BaseSettings):

    DEPLOY_ENV: Optional[DeployEnvEnum] = DeployEnvEnum.LOCAL

    LOG_LEVEL: LogLevelEnum = LogLevelEnum.INFO

    # Database settings
    DATABASE_HOST: Optional[str]
    DATABASE_USER: Optional[str]
    DATABASE_PSWD: Optional[str]
    DATABASE_NAME: Optional[str]
    DATABASE_PORT: Optional[int] = 5432
    DATABASE_URL: Optional[str]

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
    ARMADA_CLAIMS_KEY: str = "https://www.armada-hpc.com"

    # Sentry configuration
    SENTRY_DSN: Optional[HttpUrl]
    SENTRY_SAMPLE_RATE: Optional[float] = Field(1.0, gt=0.0, le=1.0)

    @root_validator
    def calculate_db_url(cls, values):
        db_url = values.get("DATABASE_URL")
        if not db_url:
            expected_keys = {
                "DATABASE_USER",
                "DATABASE_PSWD",
                "DATABASE_HOST",
                "DATABASE_PORT",
                "DATABASE_NAME",
            }
            missing_keys = expected_keys - set({k: v for (k, v) in values.items() if v is not None})
            if len(missing_keys) > 0:
                raise ValueError(f"Missing required database settings: {', '.join(sorted(missing_keys))}")

            db_url = URL.build(
                scheme="postgresql",
                user=values.get("DATABASE_USER"),
                password=values.get("DATABASE_PSWD"),
                host=values.get("DATABASE_HOST"),
                port=values.get("DATABASE_PORT"),
                path="/{}".format(values.get("DATABASE_NAME")),
            )
        elif not db_url.startswith("sqlite"):
            # Will url-escapse special characters
            db_url = URL(values["DATABASE_URL"])
        else:
            # For special case of sqlite db url (testing), do not url-escape
            pass

        values["DATABASE_URL"] = str(db_url)
        return values

    class Config:
        env_file = ".env"


settings = Settings()
