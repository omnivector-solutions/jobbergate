"""
Methods for creating connections to legacy and nextgen databases.
"""

from psycopg import connect, ClientCursor
from psycopg.rows import dict_row
from contextlib import contextmanager

from loguru import logger

from slurp.config import settings


def build_url(is_legacy=False):
    """
    Builds a postgres uri for either legacy or nextgen databases based on settings.
    """
    env_prefix = "NEXTGEN" if not is_legacy else "LEGACY"
    keys = ("user", "pswd", "host", "port", "name")
    return "postgresql://{user}:{pswd}@{host}:{port}/{name}".format(
        **{k: getattr(settings, f"{env_prefix}_DATABASE_{k.upper()}") for k in keys}
    )


@contextmanager
def db(is_legacy=False, **kwargs):
    """
    Creates a connections to the database.

    Used as a context manager that closes the connection automatically on exit.
    Legacy connections will roll-back before close as they are always read-only.
    Nextgen connections will be committed before close unless there is an error.
    """
    database_url = build_url(is_legacy=is_legacy)
    logger.info(f"Starting a connection with {database_url}")
    with connect(database_url, cursor_factory=ClientCursor, row_factory=dict_row) as connection:
        try:
            logger.info(f"Creating cursor for {database_url}")
            with connection.cursor(**kwargs) as cursor:
                yield cursor

            logger.info(f"Finalizing transaction for {database_url}")
            if not is_legacy:
                logger.info(f"Committed transaction for {database_url}")
                connection.commit()
            else:
                logger.info(f"Rolling back read-only transaction for {database_url}")
                connection.rollback()
        except Exception as err:
            logger.error(f"Hit an error in transaction for {database_url}: {err}")
            connection.rollback()
            raise

def reset_id_seq(db, table_name, column="id", reset_buffer=100):
    logger.debug(f"Resetting sequence for {table_name}.{column}")

    sequence_name = db.execute(
        f"select pg_get_serial_sequence('{table_name}', '{column}') as sequence_name"
    ).fetchone()["sequence_name"]
    logger.debug(f"Found sequence named '{sequence_name}'")

    max_id = db.execute(f"select max(id) as max_id from {table_name}").fetchone()["max_id"]
    logger.debug(f"Max of column '{column}' is {max_id}")

    reset_value = max_id + reset_buffer
    db.execute(f"alter sequence {sequence_name} restart with {reset_value}")
    logger.debug(f"Sequence reset")
