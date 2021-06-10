"""
Database model for the ApplicationPermission.
"""
from sqlalchemy import Integer, String, Table
from sqlalchemy.sql.schema import Column

from jobbergateapi2.metadata import metadata

application_permissions_table = Table(
    "application_permissions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("acl", String, nullable=False, unique=True),
)
