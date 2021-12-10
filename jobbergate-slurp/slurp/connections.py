"""
Methods for creating connections to databases.
"""

from contextlib import contextmanager

from loguru import logger
from psycopg import connect
from psycopg.rows import dict_row

from slurp.config import settings, DatabaseEnv


def build_url(db_env: DatabaseEnv = DatabaseEnv.NEXTGEN):
    """
    Builds a postgres uri for the specified environment.
    """
    keys = ('user', 'pswd', 'host', 'port', 'name')
    return "postgresql://{user}:{pswd}@{host}:{port}/{name}".format(
        **{k: getattr(settings, f'{db_env}_DATABASE_{k.upper()}') for k in keys}
    )


@contextmanager
def db(db_env: DatabaseEnv = DatabaseEnv.NEXTGEN):
    """
    Creates a connections to the database.

    Used as a context manager that closes the connection automatically on exit.
    Legacy connections will roll-back before close as they are always read-only.
    Nextgen connections will be committed before close unless there is an error.
    """
    database_url = build_url(db_env)
    logger.debug(f"Starting a connection for {db_env} environment with {database_url}")
    with connect(database_url, row_factory=dict_row) as connection:
        try:
            logger.debug(f"Creating cursor for {database_url}")
            with connection.cursor() as cursor:
                yield cursor

            logger.debug(f"Finalizing transaction for {database_url}")
            if not db_env == DatabaseEnv.LEGACY:
                logger.debug(f"Committed transaction for {database_url}")
                connection.commit()
            else:
                logger.debug(f"Rolling back read-only transaction for {database_url}")
                connection.rollback()
        except Exception as err:
             logger.error(f"Hit an error in transaction for {database_url}: {err}")
             connection.rollback()
             raise
