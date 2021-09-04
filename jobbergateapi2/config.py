"""
Configuration file, sets all the necessary environment variables, it is better used with a .env file
"""
from pydantic import BaseSettings, Field, HttpUrl

_DB_RX = r"^(sqlite|postgres)://.+$"


class Settings(BaseSettings):
    DATABASE_URL: str = Field("sqlite:///./sqlite.db?check_same_thread=true", regex=_DB_RX)
    TEST_ENV: bool = Field(False)
    S3_STAGE: str = Field("staging")
    S3_REGION: str = Field("eu-north-1")
    S3_BASE_PATH: str = Field("jobbergate-resources")
    # BACKEND_CORS_ORIGINS example: "['https://example1.com', 'https://example2.com']"
    BACKEND_CORS_ORIGINS: str = Field("[]")

    # Security Settings. For details, see https://github.com/omnivector-solutions/armada-security
    ARMASEC_SECRET: str
    ARMASEC_ALGORITHM: str = Field("RS256")
    ARMASEC_ISSUER: HttpUrl = Field(None)
    ARMASEC_CLIENT_ID: str
    ARMASEC_DOMAIN: str
    ARMASEC_AUDIENCE: HttpUrl
    ARMASEC_DEBUG: bool = Field(False)

    class Config:
        env_file = ".env"


settings = Settings()
