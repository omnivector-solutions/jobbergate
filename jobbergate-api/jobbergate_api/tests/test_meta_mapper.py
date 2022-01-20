from collections import namedtuple

import pytest

from jobbergate_api.meta_mapper import MetaField, MetaMapper


def test___init___successfully_populates_field_dict():
    instance = MetaMapper(
        foo=MetaField(description="foo description", example="foo example",),
        bar=MetaField(example="bar example",),
        baz=MetaField(description="baz description",),
    )
    assert instance.field_dict["foo"].description == "foo description"
    assert instance.field_dict["foo"].example == "foo example"
    assert instance.field_dict["bar"].description is None
    assert instance.field_dict["bar"].example == "bar example"
    assert instance.field_dict["baz"].description == "baz description"
    assert instance.field_dict["baz"].example is None


def test___init___fails_if_keyword_argument_is_not_a_MetaField():
    ValidDuckField = namedtuple("ValidDuckField", ["description", "example"])
    InvalidDuckField = namedtuple("InvalidDuckField", ["description"])

    MetaMapper(foo=ValidDuckField(description="foo description", example="foo example"))  # type:ignore
    with pytest.raises(ValueError, match="Keyword argument 'foo' does not have attribute 'example'"):
        MetaMapper(foo=InvalidDuckField(description="foo description"))  # type:ignore
