"""Functionalities to be shared by all models."""
from datetime import datetime
from pathlib import PurePath

from sqlalchemy import Column, DateTime, Integer, String, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm.decl_api import declarative_mixin
from sqlalchemy.orm.mapper import Mapper
from sqlalchemy.sql import functions

Base = declarative_base()


def _as_dict(object):
    """Transform the SQLAlchemy model to a dictionary. It also returns the relations."""
    mapper: Mapper = inspect(object).mapper
    return {
        **{col.key: getattr(object, col.key) for col in mapper.column_attrs},
        **{
            rel: getattr(object, rel) if getattr(object, rel) is not None else []
            for rel in mapper.relationships.keys()
        },
    }


@declarative_mixin
class BaseFieldsMixin:
    """
    Common resources between all tables.

    The attributes define rows and the methods API-level resources.
    """

    id: int = Column(Integer, primary_key=True)
    created_at: datetime = Column(DateTime(timezone=True), nullable=False, default=functions.now())
    updated_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        default=functions.now(),
        onupdate=functions.current_timestamp(),
    )

    def as_dict(self):
        """Transform the SQLAlchemy model to a dictionary. It also returns the relations."""
        return _as_dict(self)


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

    file_key: str = Column(String, nullable=False)

    @hybrid_property
    def filename(self):
        return PurePath(self.file_key).name
