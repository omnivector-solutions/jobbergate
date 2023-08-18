"""Define app-wide, reusable pydantic schemas."""

from typing import Any

import sqlalchemy
from pendulum.datetime import DateTime
from pydantic import BaseModel
from pydantic.utils import GetterDict


class IgnoreLazyGetterDict(GetterDict):
    """
    A custom GetterDict to avoid triggering lazy-loads when accessing attributes.

    In this way, only explicitly joined relationships will be loaded and included in the response.

    References:
        https://github.com/tiangolo/fastapi/discussions/5942
    """

    def __getitem__(self, key: str) -> Any:
        """
        Customize __getitem__ to avoid triggering lazy-loads when accessing attributes.
        """
        if self._is_lazy_loaded(key):
            raise KeyError(f"The attribute '{key}' is not loaded.")
        super().__getitem__(key)

    def get(self, key: Any, default: Any = None) -> Any:
        """
        Get an attribute value from the object, or return a default value if the attribute does not exist.
        """
        if self._is_relationship(key) and self._is_lazy_loaded(key):
            return default
        return getattr(self._obj, key, default)

    def _is_lazy_loaded(self, key: Any) -> bool:
        return key in sqlalchemy.orm.attributes.instance_state(self._obj).unloaded  # type: ignore

    def _is_relationship(self, key: Any):
        relationship_keys = [r.key for r in sqlalchemy.inspect(self._obj.__class__).relationships]
        return key in relationship_keys


class TableResource(BaseModel):
    """
    Describes a base for table models that include basic, common info.
    """

    id: int
    name: str
    owner_email: str
    created_at: DateTime
    updated_at: DateTime
    is_archived: bool
    description: str | None

    class Config:
        orm_mode = True
        getter_dict = IgnoreLazyGetterDict


class ListParams(BaseModel):
    """
    Describe the shared parameters for a list request.
    """

    sort_ascending: bool = True
    user_only: bool = False
    search: str | None
    sort_field: str | None
    include_archived: bool = False
    include_parent: bool = False
