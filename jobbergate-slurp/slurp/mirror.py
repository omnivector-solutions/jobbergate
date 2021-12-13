"""
Provides logic for mirroring application data from nextgen db to nextgen mirror.
"""
import subprocess
import tempfile
from loguru import logger
from tempenv import TemporaryEnvironment

from slurp.config import settings


def reflect():
    """
    Mirrors data from nextgen database.
    """
    logger.debug("Mirroring applications from nextgen database")
    with tempfile.TemporaryDirectory() as tmp_dir:
        pgpass_template = "{host}:{port}:{name}:{user}:{pswd}"
        pgpass_filename= f"{tmp_dir.name}/.pgpass"
        logger.debug(f"Creating temporary pgpass file {pgpass_filename}")
        with open(pgpass_filename, "w") as pgpass_file:
            print(
                pgpass_template.format(
                    host=settings.NEXTGEN_DATABASE_HOST,
                    port=settings.NEXTGEN_DATABASE_PORT,
                    name=settings.NEXTGEN_DATABASE_NAME,
                    user=settings.NEXTGEN_DATABASE_USER,
                    pswd=settings.NEXTGEN_DATABASE_PSWD,
                ),
                file=pgpass_file,
            )
            print(
                pgpass_template.format(
                    host=settings.MIRROR_DATABASE_HOST,
                    port=settings.MIRROR_DATABASE_PORT,
                    name=settings.MIRROR_DATABASE_NAME,
                    user=settings.MIRROR_DATABASE_USER,
                    pswd=settings.MIRROR_DATABASE_PSWD,
                ),
                file=pgpass_file,
            )

        dump_filename= f"{tmp_dir.name}/dumpfile"
        with TemporaryEnvironment(dict(PGPASSFILE=pgpass_filename)):
            logger.debug(f"Dumping nextgen db to file {dump_filename}")
            subrpocess.run(
                [
                    "pg_dump",
                    f"--host={settings.NEXTGEN_DATABASE_HOST}",
                    f"--port={settings.NEXTGEN_DATABASE_PORT}",
                    f"--username={settings.NEXTGEN_DATABASE_USER}",
                    f"--dbname={settings.NEXTGEN_DATABASE_NAME}",
                    f"--file={dump_filename}",
                ],
                check=True,
            )

            logger.debug(f"Restoring mirror db from file {dump_filename}")
            subrpocess.run(
                [
                    "pg_restore",
                    f"--host={settings.MIRROR_DATABASE_HOST}",
                    f"--port={settings.MIRROR_DATABASE_PORT}",
                    f"--username={settings.MIRROR_DATABASE_USER}",
                    f"--dbname={settings.MIRROR_DATABASE_NAME}",
                    f"--file={dump_filename}",
                ],
                check=True,
            )

    logger.debug("Finished mirroring applications")
