"""Test the smart template model."""

import json

import pytest
from asyncpg.exceptions import UniqueViolationError
from sqlalchemy import insert

from jobbergate_api.apps.smart_templates.models import SmartTemplate

# Force the async event loop at the app to begin.
# Since this is a time consuming fixture, it is just used where strict necessary.
pytestmark = pytest.mark.usefixtures("startup_event_force")


@pytest.fixture(scope="module")
def dummy_values():
    """Return a dictionary with dummy values."""
    return dict(
        name="test-name",
        identifier="test-identifier",
        description="test-description",
        owner_email="owner_email@test.com",
        runtime_config={"output_dir": "/tmp"},
    )


@pytest.mark.asyncio
async def test_smart_templates__success(dummy_values, time_frame):
    """
    Test that smart template table is created and populated correctly.

    Note:
        For the jsonb fields is not deserialized, so we need to use json.dumps.
        This should not be a problem when combined with Pydantic models.
    """
    expected_value = SmartTemplate(**dummy_values)

    with time_frame() as window:
        insert_query = insert(SmartTemplate).returning(SmartTemplate)
        data = await database.fetch_one(query=insert_query, values=dummy_values)

    assert data is not None

    actual_value = SmartTemplate(**data._mapping)

    assert actual_value.created_at in window
    assert actual_value.updated_at in window
    assert isinstance(actual_value.id, int)

    assert actual_value.name == expected_value.name
    assert actual_value.identifier == expected_value.identifier
    assert actual_value.description == expected_value.description
    assert actual_value.owner_email == expected_value.owner_email
    assert actual_value.runtime_config == json.dumps(expected_value.runtime_config)

    assert actual_value.file_key == f"smart_templates/{actual_value.id}/jobbergate.py"


@pytest.mark.asyncio
async def test_smart_templates__error_duplicated_identifier(dummy_values):
    """Test the smart template table raises and error when facing a duplicated identifier."""
    insert_query = insert(SmartTemplate).returning(SmartTemplate)
    data = await database.fetch_one(query=insert_query, values=dummy_values)
    assert data is not None

    with pytest.raises(
        UniqueViolationError,
        match='duplicate key value violates unique constraint "ix_smart_templates_identifier"',
    ):
        await database.fetch_one(query=insert_query, values=dummy_values)
