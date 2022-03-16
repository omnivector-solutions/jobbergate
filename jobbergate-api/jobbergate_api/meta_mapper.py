"""
Provides a metadata-mapper for re-using descriptions and examples across many pydantic models.
"""

from dataclasses import dataclass, fields
from typing import Any, Dict, Optional


@dataclass
class MetaField:
    """
    Provides a dataclass that describes the metadata that will be mapped for an individual field.
    """

    description: Optional[str] = None
    example: Optional[Any] = None


class MetaMapper:
    """
    Maps re-usable metadata for fields. Should be used with the `schema_extra` property of a Model's Config.

    Example::

        foo_meta = MetaMapper(
            id=MetaField(
                description="The unique identifier of this Foo",
                example=13,
            ),
            name=MetaField(
                description="The name of this Foo",
                example="Bar",
            ),
            is_active=MetaField(
                description="Indicates if this Foo is active",
                example=True,
            ),
            created_at=MetaField(
                description="The timestamp indicating when this Foo was created",
                example="2021-12-29 11:58:00",
            ),
        )


        class CreateFooRequest(BaseModel):
            name: str
            is_active: Optional[bool]

            class Config:
                schema_extra = foo_meta


        class UpdateFooRequest(BaseModel):
            name: Optional[str] = None
            is_active: Optional[bool] = None

            class Config:
                schema_extra = foo_meta


        class FooResponse(BaseModel):
            id: int
            name: str
            is_active: bool
            created_at: DateTime

            class Config:
                schema_extra = foo_meta


    Notice in this example that the fields may be required in some models and optional in others. Further,
    not all the fields are present in all the models. The MetaMapper allows the models to share field metadata
    and yet define the fields independently.
    """

    field_dict: Dict[str, MetaField]

    def __init__(self, **kwargs: MetaField):
        """
        Map the kwargs into the field_dict.

        All kwargs *should* be MetaFields, but any object duck-typed to include all the attributes of a
        MetaField will be accepted.
        """
        required_fields = (f.name for f in fields(MetaField))
        for (key, value) in kwargs.items():
            for field in required_fields:
                if not hasattr(value, field):
                    raise ValueError(
                        f"Keyword argument '{key}' does not have attribute '{field}'. "
                        "All keyword arguments must be MetaFields (or matching duck-typed objects)"
                    )
        self.field_dict = dict(**kwargs)

    def __call__(self, schema: Dict[str, Any], *_) -> None:
        """
        Map the MetaFields onto the metadata properties of a schema.

        Should be used in a pydantic Model's Config class.
        """
        for (key, old_metadata) in schema["properties"].items():
            new_metadata = self.field_dict.get(key)
            if new_metadata is None:
                continue

            if new_metadata.description is not None:
                old_metadata["description"] = new_metadata.description

            if new_metadata.example is not None:
                old_metadata["example"] = new_metadata.example
