"""
Persistent data storage
"""
import contextlib
import json
import re

import asyncpg
import databases
import fastapi
import sqlalchemy

from jobbergate_api.config import settings
from jobbergate_api.metadata import metadata

database = databases.Database(settings.DATABASE_URL)  # type: ignore


def create_all_tables():
    """
    Create all the tables in the database
    """
    engine = sqlalchemy.create_engine(settings.DATABASE_URL)

    metadata.create_all(engine)



@contextlib.contextmanager
def handle_fk_error():
    """
    This method is used to unpack metadata from a ForeignKeyViolationError
    """
    try:
        yield
    except asyncpg.exceptions.ForeignKeyViolationError as err:
        FK_DETAIL_RX = r"DETAIL:  Key \(id\)=\((?P<pk_id>\d+)\) is still referenced from table \"(?P<table>\w+)\""
        matches = re.search(FK_DETAIL_RX, str(err), re.MULTILINE)
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_409_CONFLICT,
            detail=dict(
                message="Delete failed due to foreign-key constraint",
                table=matches.group("table") if matches else None,
                pk_id=matches.group("pk_id") if matches else None,
            ),
        )
