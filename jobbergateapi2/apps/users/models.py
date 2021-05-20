"""
Database model for the User resource
"""
from sqlalchemy import Boolean, DateTime, Integer, String, Table
from sqlalchemy.sql import func
from sqlalchemy.sql.schema import Column

from jobbergateapi2.metadata import metadata

users_table = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("email", String, nullable=False, index=True, unique=True),
    Column("is_superuser", Boolean, nullable=False, default=False),
    Column("is_active", Boolean, nullable=False, default=True),
    Column("full_name", String, nullable=False, unique=True),
    Column("password", String, nullable=False),
    Column("data_joined", DateTime, nullable=False, default=func.now()),
)
