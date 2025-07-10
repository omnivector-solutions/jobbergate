"""
Provide configuration settings for the app.

Pull settings from environment variables or a .env file if available.
"""

from enum import Enum
from typing import Annotated, Optional

from buzz import require_condition
from loguru import logger
from pydantic import confloat, Field, HttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevelEnum(str, Enum):
    """
    Provide an enumeration class describing the available log levels.
    """

    TRACE = "TRACE"
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
    SQL_LOG_LEVEL: LogLevelEnum = LogLevelEnum.WARNING

    # Database settings  # Default to values from docker-compose.yml
    DATABASE_HOST: str = "localhost"
    DATABASE_USER: str = "local-user"
    DATABASE_PSWD: str = "local-pswd"
    DATABASE_NAME: str = "local-db"
    DATABASE_PORT: int = 5432
    DATABASE_POOL_SIZE: int = 20
    DATABASE_POOL_MAX_OVERFLOW: int = 20
    DATABASE_POOL_PRE_PING: bool = False

    # Test database settings
    TEST_DATABASE_HOST: str = "localhost"
    TEST_DATABASE_USER: str = "test-user"
    TEST_DATABASE_PSWD: str = "test-pswd"
    TEST_DATABASE_NAME: str = "test-db"
    TEST_DATABASE_PORT: int = 5433

    # S3 configuration
    S3_BUCKET_NAME: str = Field("jobbergate-staging-eu-north-1-resources")
    S3_ENDPOINT_URL: Optional[str] = None

    # Test S3 configuration
    TEST_S3_BUCKET_NAME: str = Field("test-jobbergate-resources")
    TEST_S3_ENDPOINT_URL: str = Field("http://localhost:9000")

    # RabbitMQ configuration
    RABBITMQ_HOST: Optional[str] = None
    RABBITMQ_USERNAME: Optional[str] = None
    RABBITMQ_PASSWORD: Optional[str] = None
    RABBITMQ_DEFAULT_EXCHANGE: str = "default"

    # Security Settings. For details, see https://github.com/omnivector-solutions/armasec
    ARMASEC_DOMAIN: str
    ARMASEC_USE_HTTPS: bool = Field(True)
    ARMASEC_DEBUG: bool = Field(False)
    ARMASEC_ADMIN_DOMAIN: Optional[str] = None
    ARMASEC_ADMIN_MATCH_KEY: Optional[str] = None
    ARMASEC_ADMIN_MATCH_VALUE: Optional[str] = None

    # Key to custom claims packaged with Auth0 tokens
    IDENTITY_CLAIMS_KEY: str = "https://omnivector.solutions"

    # Sentry configuration
    SENTRY_DSN: Optional[HttpUrl] = None
    SENTRY_TRACES_SAMPLE_RATE: Annotated[float, confloat(gt=0, le=1.0)] = 0.01
    SENTRY_SAMPLE_RATE: Annotated[float, confloat(gt=0.0, le=1.0)] = 0.25
    SENTRY_PROFILING_SAMPLE_RATE: Annotated[float, confloat(gt=0.0, le=1.0)] = 0.01

    # Maximum number of bytes allowed for file uploads
    MAX_UPLOAD_FILE_SIZE: int = 5 * 1024 * 1024  # 100 MB

    # Sendgrid configuration for email notification
    SENDGRID_FROM_EMAIL: Optional[str] = None
    SENDGRID_API_KEY: Optional[str] = None

    # Enable multi-tenancy so that the database is determined by the client_id in the auth token
    MULTI_TENANCY_ENABLED: bool = Field(False)

    # Automatically clean up unused job script templates
    AUTO_CLEAN_JOB_SCRIPT_TEMPLATES_DAYS_TO_ARCHIVE: int | None = None
    AUTO_CLEAN_JOB_SCRIPT_TEMPLATES_DAYS_TO_DELETE: int | None = None

    # Automatically clean up unused job scripts
    AUTO_CLEAN_JOB_SCRIPTS_DAYS_TO_ARCHIVE: int | None = None
    AUTO_CLEAN_JOB_SCRIPTS_DAYS_TO_DELETE: int | None = None

    # Automatically clean up unused job submissions
    AUTO_CLEAN_JOB_SUBMISSIONS_DAYS_TO_ARCHIVE: int | None = None
    AUTO_CLEAN_JOB_SUBMISSIONS_DAYS_TO_DELETE: int | None = None

    # Metadata for the API Documentation
    METADATA_API_TITLE: str = "Jobbergate-API"
    METADATA_CONTACT_NAME: str = "Omnivector Solutions"
    METADATA_CONTACT_URL: str = "https://omnivector.solutions"
    METADATA_CONTACT_EMAIL: str = "info@omnivector.solutions"

    @model_validator(mode="before")
    @classmethod
    def remove_blank_env(cls, values):
        """
        Remove any settings from the environment that are blank strings.

        This allows the defaults to be set if ``docker-compose`` defaults a missing
        environment variable to a blank string.
        """
        clean_values = dict()
        for key, value in values.items():
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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
