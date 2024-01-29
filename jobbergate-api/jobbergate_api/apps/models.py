"""Functionalities to be shared by all models."""

from typing import cast

from inflection import tableize
from pendulum.datetime import DateTime as PendulumDateTime
from snick import conjoin
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column
from sqlalchemy.sql.expression import Select


class Base(DeclarativeBase):
    """
    Base class for all models.

    References:
        https://docs.sqlalchemy.org/en/20/orm/declarative_mixins.html
    """


class CommonMixin:
    """
    Provide a dynamic table and helper methods for displaying instances.
    """

    @declared_attr.directive
    @classmethod
    def __tablename__(cls) -> str:
        """
        Dynamically create table name based on the class name.
        """
        return tableize(cls.__name__)

    def _iter_cols(self):
        """
        Iterate over the columns of the class.
        """
        for col in inspect(self.__class__).columns.keys():
            yield (col, getattr(self, col))

    def __str__(self):
        """
        Produce a pretty string representation of the class instance.
        """
        primary_keys = [pk.name for pk in inspect(self.__class__).primary_key]
        primary_key_str = ", ".join([f"{pk}: {getattr(self, pk)}" for pk in primary_keys])
        return conjoin(
            f"{self.__class__.__name__}: ({primary_key_str})",
            *[f"{k}: {v}" for (k, v) in self._iter_cols() if k not in primary_keys],
            join_str="\n  ",
        )


class IdMixin:
    """
    Provide an id primary_key column.

    Attributes:
        id: The id of the job script template.
        cloned_from: Specify the id of the row that this row was cloned from.
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    @declared_attr
    def cloned_from_id(cls) -> Mapped[int | None]:
        """
        Dynamically create a cloned_from_id column.
        """
        return mapped_column(
            Integer,
            ForeignKey(cast(Column[int], cls.id), name="clone", ondelete="SET NULL"),
            nullable=True,
        )


class TimestampMixin:
    """
    Add timestamp columns to a table.

    Attributes:
        created_at: The date and time when the job script template was created.
        updated_at: The date and time when the job script template was updated.
    """

    created_at: Mapped[PendulumDateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=PendulumDateTime.utcnow
    )
    updated_at: Mapped[PendulumDateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=PendulumDateTime.utcnow,
        onupdate=PendulumDateTime.utcnow,
    )


class OwnerMixin:
    """
    Add an owner email columns to a table.

    Attributes:
        owner_email: The email of the owner of the job script template.
    """

    owner_email: Mapped[str] = mapped_column(String, nullable=False, index=True)


class NameMixin:
    """
    Add name and description columns to a table.

    Attributes:
        name: The name of the job script template.
        description: The description of the job script template.
    """

    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String, default="")


class ArchiveMixin:
    """
    Add is_archived column to a table.

    Attributes:
        is_archived: Specify is a row is considered archived, hidden it by default when listing rows.
    """

    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CrudMixin(CommonMixin, IdMixin, TimestampMixin, OwnerMixin, NameMixin, ArchiveMixin):
    """
    Add needed columns and declared attributes for all models that support a CrudService.
    """

    @classmethod
    def searchable_fields(cls):
        """
        Describe the fields that may be used in search queries.
        """
        return {
            cls.name,
            cls.description,
            cls.owner_email,
        }

    @classmethod
    def sortable_fields(cls):
        """
        Describe the fields that may be used for sorting queries.
        """
        return {
            cls.id,
            cls.name,
            cls.owner_email,
            cls.created_at,
            cls.updated_at,
        }

    @classmethod
    def include_files(cls, query: Select) -> Select:
        """
        Include custom options on a query to eager load files.

        This should be overridden by derived classes.
        """
        raise NotImplementedError(
            f"Derived classes should override include_files. {cls.__tablename__} does not include it."
        )

    @classmethod
    def include_parent(cls, query: Select) -> Select:
        """
        Include custom options on a query to eager load parent data.

        This should be overridden by derived classes.
        """
        raise NotImplementedError(
            f"Derived classes should override include_parent. {cls.__tablename__} does not include it."
        )


class FileMixin(CommonMixin, TimestampMixin):
    """
    Add needed columns and declared attributes for all models that support a FileService.

    Attributes:
        parent_id:   The id of the parent row in another table.
                     Note: Derived classes should override this attribute to make it a foreign key as well.
        description: The description of the job script template.
    """

    parent_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String, primary_key=True)

    @hybrid_property
    def file_key(self) -> str:
        """
        Dynamically define the s3 key for the file.
        """
        return f"{self.__tablename__}/{self.parent_id}/{self.filename}"
