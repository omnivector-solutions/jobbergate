#!/usr/bin/env python

from random import randint, random


from typing import Optional

from pydantic import BaseSettings


class Settings(BaseSettings):

    FAIL_PERCENTAGE: float = 0.1

    @root_validator
    def validate(cls, values):
        """
        Compute settings values that are based on other settings values.
        """
        # Validate fail pctg

        return values

    class Config:
        """
        Customize behavior of the Settings class. Especially, enable the use of dotenv to load settings from a ``.env``
        file instead of the environment.
        """
        env_file = "fake-sbatch.env"


settings = Settings()


def main():
    pass


if __name__ == '__main__':
    main()
