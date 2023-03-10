"""Functionalities to be shared by all models."""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, registry
from sqlalchemy.orm.decl_api import DeclarativeMeta, declarative_mixin
from sqlalchemy.sql import functions

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

    Attributes:
        created_at: The date and time when the row was created.
        updated_at: The date and time when the row was updated.
    """

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=functions.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=functions.now(),
        onupdate=functions.current_timestamp(),
    )


@declarative_mixin
class ExtraFieldsMixin:
    """
    Common resources between all tables.

    The attributes define rows and the methods API-level resources.

    Attributes:
        name: The name of the resource.
        description: The description of the resource.
        owner_email: The email of the owner of the resource.
    """

    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String, default="")
    owner_email: Mapped[str] = mapped_column(String, nullable=False, index=True)