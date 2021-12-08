"""
Persistent data storage
"""
import databases
import sqlalchemy

from jobbergate_api.config import settings
from jobbergate_api.metadata import metadata

database = databases.Database(settings.DATABASE_URL)


def create_all_tables():
    """
    Create all the tables in the database
    """
    engine = sqlalchemy.create_engine(settings.DATABASE_URL)

    metadata.create_all(engine)
