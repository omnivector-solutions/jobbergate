"""Define app-wide, reusable pydantic schemas."""

import datetime
from typing import Annotated, Any, List, Type

import pendulum
from pydantic import BaseModel, ConfigDict, Field, GetCoreSchemaHandler
from pydantic_core import PydanticCustomError, core_schema

# Make both Pydantic and mypy happy:
LengthLimitedStr = Annotated[str, Field(max_length=255)]


class PydanticDateTime(pendulum.DateTime):
    """
    A `pendulum.DateTime` object. At runtime, this type decomposes into pendulum.DateTime automatically.

    This type exists because Pydantic throws a fit on unknown types.

    This code is borrowed and enhanced from the `pydantic-extra-types` module but provides conversion from
    standard datetimes as well.
    """

    __slots__: List[str] = []

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: Type[Any], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        """
        Return a Pydantic CoreSchema with the Datetime validation.

        Args:
            source: The source type to be converted.
            handler: The handler to get the CoreSchema.

        Returns:
            A Pydantic CoreSchema with the Datetime validation.
        """
        return core_schema.no_info_wrap_validator_function(cls._validate, core_schema.datetime_schema())

    @classmethod
    def _validate(cls, value: Any, handler: core_schema.ValidatorFunctionWrapHandler) -> Any:
        """
        Validate the datetime object and return it.

        Args:
            value: The value to validate.
            handler: The handler to get the CoreSchema.

        Returns:
            The validated value or raises a PydanticCustomError.
        """
        if isinstance(value, pendulum.DateTime):
            return handler(value)

        if isinstance(value, datetime.datetime):
            return handler(pendulum.instance(value))

        try:
            return handler(pendulum.parse(value))
        except Exception as exc:
            raise PydanticCustomError("value_error", "value is not a valid timestamp") from exc


class TableResource(BaseModel):
    """
    Describes a base for table models that include basic, common info.
    """

    id: int
    name: str
    owner_email: str
    created_at: PydanticDateTime
    updated_at: PydanticDateTime
    is_archived: bool
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ListParams(BaseModel):
    """
    Describe the shared parameters for a list request.
    """

    sort_ascending: bool = True
    user_only: bool = False
    search: LengthLimitedStr | None = None
    sort_field: LengthLimitedStr | None = None
    include_archived: bool = False
    include_parent: bool = False
