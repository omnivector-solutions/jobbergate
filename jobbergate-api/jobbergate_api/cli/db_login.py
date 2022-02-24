import subprocess

from jobbergate_api.config import settings


def db_login():
    subprocess.run(["pgcli", settings.DATABASE_URL])
