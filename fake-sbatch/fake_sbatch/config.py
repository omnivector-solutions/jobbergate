from pathlib import Path

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    FAKE_SBATCH_FAIL_PCT: float = Field(0.1, ge=0.0, le=1.0)
    FAKE_SBATCH_MAX_JOB_ID: int = 1_000_000
    FAKE_SBATCH_MIN_JOB_ID: int = 1

    class Config:
        env_file = Path(".env")


settings = Settings()
