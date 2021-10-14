import subprocess

from jobbergateapi2.config import settings


def login():
    subprocess.run(["pgcli", settings.DATABASE_URL])
