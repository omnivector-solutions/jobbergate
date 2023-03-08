"""Functionalities to be shared by all models."""
from datetime import datetime

from sqlalchemy import Column, DateTime, String, inspect
from sqlalchemy.orm.decl_api import declarative_mixin
from sqlalchemy.orm.mapper import Mapper
from sqlalchemy.sql import functions

from sqlalchemy.orm import registry
from sqlalchemy.orm.decl_api import DeclarativeMeta

mapper_registry = registry()


class Base(metaclass=DeclarativeMeta):
    """
    Base class for all models.

    References:
        https://docs.sqlalchemy.org/en/14/orm/declarative_styles.html#creating-an-explicit-base-non-dynamically-for-use-with-mypy-similar
    """

    __abstract__ = True

    registry = mapper_registry
    metadata = mapper_registry.metadata

    __init__ = mapper_registry.constructor


@declarative_mixin
class BaseFieldsMixin:
    """
    Common resources between all tables.

    The attributes define rows and the methods API-level resources.
    """

    created_at: datetime = Column(DateTime, nullable=False, default=functions.now())
    updated_at: datetime = Column(
        DateTime,
        nullable=False,
        default=functions.now(),
        onupdate=functions.current_timestamp(),
    )


@declarative_mixin
class NameDescriptionEmailMixin:
    """
    Common resources between all tables.

    The attributes define rows and the methods API-level resources.
    """

    name = Column(String, nullable=False)
    description = Column(String, default="")
    owner_email = Column(String, nullable=False, index=True)


@declarative_mixin
class FileMixin:
    """
    Common resources between all tables.

    The attributes define rows and the methods API-level resources.
    """

    filename: str = Column(String, nullable=False)
