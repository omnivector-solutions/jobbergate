"""
Provide command for starting a local development server for the API.
"""
from time import sleep

import typer
import uvicorn
from loguru import logger
from sqlalchemy import create_engine

from jobbergate_api.storage import build_db_url


def _wait_for_db(wait_count, wait_interval):
    """
    Wait for a database connection.

    Loop for a maximum of ``wait_count`` times where each lasts for ``wait_interval`` seconds. If the
    connection resolves before the time is up, return normally. If the database fails to connect, raise a
    ``RuntimeError``.
    """
    database_url = build_db_url()
    logger.debug(f"database url is: {build_db_url()}")
    count = 0
    while count < wait_count:
        logger.debug(f"Checking health of database at {database_url}: Attempt #{count}")
        count += 1
        try:
            engine = create_engine(database_url)
            with engine.connect() as db:
                db.execute("select version()")
            return
        except Exception as err:
            logger.warning(f"Database is not yet healthy: {err}")
        sleep(wait_interval)

    raise RuntimeError("Could not connect to the database")


def dev_server(
    db_wait_count: int = typer.Option(3, help="How many times to attempt a check"),
    db_wait_interval: float = typer.Option(5.0, help="Seconds to wait between checks"),
    port: int = typer.Option(5000, help="The port where the server should listen"),
    log_level: str = typer.Option("DEBUG", help="The level to log uvicorn output"),
):
    """
    Start a development server locally.
    """
    try:
        logger.info("Waiting for the database")
        _wait_for_db(db_wait_count, db_wait_interval)
    except Exception:
        logger.error("Database is not available")
        typer.Exit(1)

    uvicorn.run(
        "jobbergate_api.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level=log_level.lower(),
    )
