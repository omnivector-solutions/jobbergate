"""Provide protocols for CRUD and file operations in routers in a dedicated file to avoid circular imports."""

from __future__ import annotations

from typing import Protocol, TypeVar

from sqlalchemy.orm import Mapped
from sqlalchemy.sql.expression import Select


class CrudModelProto(Protocol):
    """
    Provide a protocol for models that can be operated on by the CrudService.

    This protocol enables type hints for editors and type checking with mypy.

    These services would best be served by an intersection type so that the model_type is actually
    specified to inherit from _both_ the mixins and the Base. This would allow static type checkers to
    recognize that all of the columns in a mixin are available and that the class can be
    instantiated in the create method. However, intersection types are not supported yet. For more
    information, see this discussion: https://github.com/python/typing/issues/213
    """

    id: Mapped[int]
    owner_email: Mapped[str]
    is_archived: Mapped[bool]

    def __init__(self, **kwargs):
        """
        Declare that the protocol can be instantiated.
        """
        ...

    def __tablename__(self) -> str:
        """
        Declare that the protocol has a method to dynamically produce the table name.
        """
        ...

    @classmethod
    def searchable_fields(cls) -> set[str]:
        """
        Declare that the protocol has searchable fields.
        """
        ...

    @classmethod
    def sortable_fields(cls) -> set[str]:
        """
        Declare that the protocol has sortable fields.
        """
        ...

    @classmethod
    def include_files(cls, query: Select) -> Select:
        """
        Declare that the protocol has a method to include files in a query.
        """
        ...

    @classmethod
    def include_parent(cls, query: Select) -> Select:
        """
        Declare that the protocol has a method to include details about the parent entry in a query.
        """
        ...


CrudModel = TypeVar("CrudModel", bound=CrudModelProto)


class FileModelProto(Protocol):
    """
    Provide a protocol for models that can be operated on by the FileService.

    This protocol enables type hints for editors and type checking with mypy.

    These services would best be served by an intersection type so that the model_type is actually
    specified to inherit from _both_ the mixins and the Base. This would allow static type checkers to
    recognize that all of the columns in a mixin are available and that the class can be
    instantiated in the create method. However, intersection types are not supported yet. For more
    information, see this discussion: https://github.com/python/typing/issues/213
    """

    parent_id: Mapped[int]
    filename: Mapped[str]
    file_key: str

    def __init__(self, **kwargs):
        """
        Declare that the protocol can be instantiated.
        """
        ...

    def __tablename__(self) -> str:
        """
        Declare that the protocol has a method to dynamically produce the table name.
        """
        ...


FileModel = TypeVar("FileModel", bound=FileModelProto)
