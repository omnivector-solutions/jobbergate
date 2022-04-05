"""
Test the ``meta_mapper()`` function and ``MetaMapper`` class.
"""

from collections import namedtuple

import pytest

from jobbergate_api.meta_mapper import MetaField, MetaMapper


def test___init___successfully_populates_field_dict():
    """
    Provide a test case for the ``MetaMapper`` class instantiator.

    Test that a MetaMapper can be successfully instantiated.
    """
    instance = MetaMapper(
        foo=MetaField(description="foo description", example="foo example"),
        bar=MetaField(example="bar example"),
        baz=MetaField(description="baz description"),
    )
    assert instance.field_dict["foo"].description == "foo description"
    assert instance.field_dict["foo"].example == "foo example"
    assert instance.field_dict["bar"].description is None
    assert instance.field_dict["bar"].example == "bar example"
    assert instance.field_dict["baz"].description == "baz description"
    assert instance.field_dict["baz"].example is None


def test___init___fails_if_keyword_argument_is_not_a_MetaField():
    """
    Provide a test case for the ``MetaMapper`` class instantiator.

    Test that a MetaMapper cannot be instantiated if a keyword argument is not an instance of ``MetaField``.
    """
    ValidDuckField = namedtuple("ValidDuckField", ["description", "example"])
    InvalidDuckField = namedtuple("InvalidDuckField", ["description"])

    MetaMapper(foo=ValidDuckField(description="foo description", example="foo example"))  # type:ignore
    with pytest.raises(ValueError, match="Keyword argument 'foo' does not have attribute 'example'"):
        MetaMapper(foo=InvalidDuckField(description="foo description"))  # type:ignore


def test__call___remaps_fields_when_they_are_present_in_the_schema_being_mapped():
    """
    Provide a test case for calling a ``MetaMapper`` instance.

    Test that dictionary fields are remapped if they have entries in the mapper.
    """
    mapper = MetaMapper(
        foo=MetaField(
            description="new foo description",
            example="new foo example",
        ),
        bar=MetaField(
            example="new bar example",
        ),
        baz=MetaField(
            description="new baz description",
        ),
    )
    full_instance = dict(
        properties=dict(
            foo=dict(
                description="foo description",
                example="foo example",
            ),
            bar=dict(
                description="bar description",
                example="bar example",
            ),
            baz=dict(
                description="baz description",
                example="baz example",
            ),
        ),
    )
    mapper(full_instance)
    assert full_instance["properties"]["foo"]["description"] == "new foo description"
    assert full_instance["properties"]["foo"]["example"] == "new foo example"
    assert full_instance["properties"]["bar"]["description"] == "bar description"
    assert full_instance["properties"]["bar"]["example"] == "new bar example"
    assert full_instance["properties"]["baz"]["description"] == "new baz description"
    assert full_instance["properties"]["baz"]["example"] == "baz example"
