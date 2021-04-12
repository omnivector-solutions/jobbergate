"""
Persistent data storage
"""
import databases
import sqlalchemy

from jobbergateapi2.apps.users.models import metadata
from jobbergateapi2.config import settings

database = databases.Database(settings.DATABASE_URL)


def create_all_tables():
    """
    Create all the tables in the database
    """
    engine = sqlalchemy.create_engine(settings.DATABASE_URL)

    metadata.create_all(engine)
