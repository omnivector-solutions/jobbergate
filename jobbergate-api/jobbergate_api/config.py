"""
Provide configuration settings for the app.

Pull settings from environment variables or a .env file if available.
"""
from enum import Enum
from typing import Optional

from buzz import require_condition
from loguru import logger
from pydantic import BaseSettings, Field, HttpUrl, root_validator


class LogLevelEnum(str, Enum):
    """
    Provide an enumeration class describing the available log levels.
    """

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


def check_none_or_all_keys_exist(input_dict: dict, target_keys: set) -> bool:
    """
    Verify if none or all of the target keys exist in the input dictionary.
    """
    all_exist = all(k in input_dict for k in target_keys)
    none_exist = all(k not in input_dict for k in target_keys)
    return all_exist or none_exist


class Settings(BaseSettings):
    """
    Provide a pydantic ``BaseSettings`` model for the application settings.
    """

    DEPLOY_ENV: str = "LOCAL"

    LOG_LEVEL: LogLevelEnum = LogLevelEnum.DEBUG

    # Database settings  # Default to values from docker-compose.yml
    DATABASE_HOST: str = "localhost"
    DATABASE_USER: str = "local-user"
    DATABASE_PSWD: str = "local-pswd"
    DATABASE_NAME: str = "local-db"
    DATABASE_PORT: int = 5432

    # Test database settings
    TEST_DATABASE_HOST: str = "localhost"
    TEST_DATABASE_USER: str = "test-user"
    TEST_DATABASE_PSWD: str = "test-pswd"
    TEST_DATABASE_NAME: str = "test-db"
    TEST_DATABASE_PORT: int = 5433

    # S3 configuration
    S3_BUCKET_NAME: str = Field("jobbergate-staging-eu-north-1-resources")
    S3_ENDPOINT_URL: Optional[str]

    # Security Settings. For details, see https://github.com/omnivector-solutions/armasec
    ARMASEC_DOMAIN: str
    ARMASEC_USE_HTTPS: bool = Field(True)
    ARMASEC_AUDIENCE: Optional[HttpUrl]
    ARMASEC_DEBUG: bool = Field(False)
    ARMASEC_ADMIN_DOMAIN: Optional[str]
    ARMASEC_ADMIN_AUDIENCE: Optional[HttpUrl]
    ARMASEC_ADMIN_MATCH_KEY: Optional[str]
    ARMASEC_ADMIN_MATCH_VALUE: Optional[str]

    # Key to custom claims packaged with Auth0 tokens
    IDENTITY_CLAIMS_KEY: str = "https://omnivector.solutions"

    # Sentry configuration
    SENTRY_DSN: Optional[HttpUrl]
    SENTRY_SAMPLE_RATE: float = Field(1.0, gt=0.0, le=1.0)

    # Maximum number of bytes allowed for file uploads
    MAX_UPLOAD_FILE_SIZE: int = 100 * 1024 * 1024  # 100 MB

    # Sendgrid configuration for email notification
    SENDGRID_FROM_EMAIL: Optional[str]
    SENDGRID_API_KEY: Optional[str]

    @root_validator(pre=True)
    def remove_blank_env(cls, values):
        """
        Remove any settings from the environment that are blank strings.

        This allows the defaults to be set if ``docker-compose`` defaults a missing
        environment variable to a blank string.
        """
        clean_values = dict()
        for (key, value) in values.items():
            if isinstance(value, str):
                if value.strip():
                    clean_values[key] = value
                else:
                    logger.warning(f"The setting {key} is a blank string and was not considered.")
            else:
                clean_values[key] = value

        require_condition(
            check_none_or_all_keys_exist(
                clean_values,
                {"SENDGRID_FROM_EMAIL", "SENDGRID_API_KEY"},
            ),
            "Either none or all SendGrind parameters are expected.",
            RuntimeError,
        )

        return clean_values

    class Config:
        env_file = ".env"


settings = Settings()
