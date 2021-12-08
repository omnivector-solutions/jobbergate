import subprocess

from jobbergate_api.config import settings


def login():
    subprocess.run(["pgcli", settings.DATABASE_URL])
