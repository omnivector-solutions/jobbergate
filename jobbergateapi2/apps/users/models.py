"""
Database model for the User resource
"""
import sqlalchemy
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.sql import func
from sqlalchemy.sql.schema import Column

metadata = sqlalchemy.MetaData()

users_table = sqlalchemy.Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("email", String, nullable=False, index=True, unique=True),
    Column("is_admin", Boolean, nullable=False, default=False),
    Column("username", String, nullable=False, unique=True),
    Column("password", String, nullable=False),
    Column("data_joined", DateTime, nullable=False, default=func.now()),
)
