from psycopg import connect
from psycopg.rows import dict_row
from contextlib import contextmanager

from loguru import logger

from slurp.config import settings


def build_url(is_legacy=False):
    env_prefix = 'NEXTGEN' if not is_legacy else 'LEGACY'
    keys = ('user', 'pswd', 'host', 'port', 'name')
    return "postgresql://{user}:{pswd}@{host}:{port}/{name}".format(
        **{k: getattr(settings, f'{env_prefix}_DATABASE_{k.upper()}') for k in keys}
    )


@contextmanager
def db(is_legacy=False):
    database_url = build_url(is_legacy=is_legacy)
    logger.debug(f"Starting a connection with {database_url}")
    with connect(database_url, row_factory=dict_row) as connection:
        try:
            logger.debug(f"Creating cursor for {database_url}")
            with connection.cursor() as cursor:
                yield cursor

            logger.debug(f"Finalizing transaction for {database_url}")
            if not is_legacy:
                logger.debug(f"Committed transaction for {database_url}")
                connection.commit()
            else:
                logger.debug(f"Rolling back read-only transaction for {database_url}")
                connection.rollback()
        except Exception as err:
             logger.error(f"Hit an error in transaction for {database_url}: {err}")
             connection.rollback()
             raise
