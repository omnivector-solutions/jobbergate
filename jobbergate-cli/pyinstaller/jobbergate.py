"""
This is the entry point for the pyinstaller build.

Notes:
    Extra imports are required to ensure jobbergate works for legacy applications.
"""
import jobbergate_cli.application_base  # noqa
import jobbergate_cli.jobberappslib  # noqa
from jobbergate_cli.main import app


if __name__ == "__main__":
    app()
