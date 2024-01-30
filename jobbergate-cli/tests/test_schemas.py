from typing import Any, Dict, Optional, TypeVar

from pydantic import BaseModel

from jobbergate_cli.schemas import ListResponseEnvelope


EnvelopeT = TypeVar("EnvelopeT")


def test_list_response_envelope_with_plain_dict():
    data = dict(
        items=[
            dict(name="item-1"),
            dict(name="item-2"),
        ],
        total=2,
        page=0,
        size=5,
        pages=1,
    )
    envelope: ListResponseEnvelope[Dict[str, Any]] = ListResponseEnvelope[Dict[str, Any]](**data)
    assert envelope.items == [
        dict(name="item-1"),
        dict(name="item-2"),
    ]
    assert envelope.total == 2
    assert envelope.page == 0
    assert envelope.size == 5
    assert envelope.pages == 1


def test_list_envelope_with_nested_model():
    data = dict(
        items=[
            dict(name="item-1"),
            dict(name="item-2"),
        ],
        total=2,
        page=0,
        size=5,
        pages=1,
    )

    class DummyModel(BaseModel):
        name: str

    dummy_envelope: ListResponseEnvelope[DummyModel] = ListResponseEnvelope[DummyModel](**data)
    assert dummy_envelope.items == [
        DummyModel(name="item-1"),
        DummyModel(name="item-2"),
    ]
    assert dummy_envelope.total == 2
    assert dummy_envelope.page == 0
    assert dummy_envelope.size == 5
    assert dummy_envelope.pages == 1

    class IdiotModel(BaseModel):
        name: str
        foo: Optional[str] = None

    idiot_envelope: ListResponseEnvelope[IdiotModel] = ListResponseEnvelope[IdiotModel](**data)
    assert idiot_envelope.items == [
        IdiotModel(name="item-1"),
        IdiotModel(name="item-2"),
    ]
    assert idiot_envelope.total == 2
    assert idiot_envelope.page == 0
    assert idiot_envelope.size == 5
    assert idiot_envelope.pages == 1
