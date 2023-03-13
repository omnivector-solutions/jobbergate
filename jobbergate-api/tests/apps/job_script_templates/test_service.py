"""Database models for the job script template resource."""
from typing import Any

import pytest
from sqlalchemy.exc import IntegrityError

from jobbergate_api.apps.job_script_templates.models import JobScriptTemplate
from jobbergate_api.apps.job_script_templates.schemas import (
    JobTemplateCreateRequest,
    JobTemplateUpdateRequest,
)
from jobbergate_api.apps.job_script_templates.service import (
    JobScriptTemplateService,
)
from jobbergate_api.database import SessionLocal

# Force the async event loop at the app to begin.
# Since this is a time consuming fixture, it is just used where strict necessary.
# pytestmark = pytest.mark.usefixtures("startup_event_force")


@pytest.fixture
async def template_service():
    """Return the services module."""
    async with SessionLocal() as session:
        yield JobScriptTemplateService(session=session)
        session.rollback()


@pytest.fixture
def template_test_data() -> dict[str, Any]:
    """Return a dictionary with dummy values."""
    return dict(
        name="test-name",
        identifier="test-identifier",
        description="test-description",
        owner_email="owner_email@test.com",
        template_vars={"output_dir": "/tmp"},
    )


@pytest.fixture
async def inserted_test_data(template_service, template_test_data) -> JobScriptTemplate:
    """Insert a JobScriptTemplate on the database and return it for reference."""
    return await template_service.create(
        incoming_data=JobTemplateCreateRequest(**template_test_data),
        owner_email=template_test_data["owner_email"],
    )


class TestCreateJobScriptTemplateService:
    @pytest.mark.asyncio
    async def test_create__success(
        self,
        template_service,
        template_test_data,
        time_frame,
        tester_email,
    ):
        """Test that the template is created successfully."""
        expected_result = JobTemplateCreateRequest(**template_test_data)

        with time_frame() as window:
            actual_result = await template_service.create(
                incoming_data=expected_result, owner_email=tester_email
            )

        assert JobTemplateCreateRequest.from_orm(actual_result) == expected_result

        assert actual_result.owner_email == tester_email
        assert actual_result.created_at in window
        assert actual_result.updated_at in window
        assert actual_result.files == []
        assert isinstance(actual_result.id, int)

    @pytest.mark.asyncio
    async def test_create_duplicate_identifier__failure(
        self,
        template_service,
        inserted_test_data,
        tester_email,
    ):
        """Test that the template creation fails when its identifiers is not unique."""
        with pytest.raises(
            IntegrityError,
            match="duplicate key value violates unique constraint",
        ):
            await template_service.create(
                incoming_data=JobTemplateCreateRequest.from_orm(inserted_test_data),
                owner_email=tester_email,
            )

    @pytest.mark.asyncio
    async def test_count__success(self, template_test_data, tester_email, template_service):
        """Test that the template is created successfully."""
        local_template_values = template_test_data.copy()
        del local_template_values["identifier"]

        test_data = JobTemplateCreateRequest(**local_template_values)

        assert await template_service.count() == 0
        for i in range(1, 4):
            await template_service.create(
                incoming_data=test_data,
                owner_email=tester_email,
            )
            assert await template_service.count() == i

    @pytest.mark.asyncio
    @pytest.mark.parametrize("identification_attribute", ("id", "identifier"))
    async def test_get__success(self, identification_attribute, template_service, inserted_test_data):
        """Test that the template is recovered successfully using multiple attributes."""
        identification = getattr(inserted_test_data, identification_attribute)

        actual_result = await template_service.get(identification)
        assert actual_result == inserted_test_data

    @pytest.mark.asyncio
    @pytest.mark.parametrize("id_or_identifier", [0, "test-identifier"])
    async def test_read__id_or_identifier_not_found(self, template_service, id_or_identifier):
        """Test that the template is read successfully."""
        result = await template_service.get(id_or_identifier)

        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize("identification_attribute", ("id", "identifier"))
    async def test_delete__success_by_id(
        self,
        identification_attribute,
        template_service,
        inserted_test_data,
    ):
        """Test that the template is read successfully."""
        identification = getattr(inserted_test_data, identification_attribute)
        assert await template_service.count() == 1
        result = await template_service.get(identification)
        assert result == inserted_test_data

        await template_service.delete(identification)
        assert await template_service.count() == 0

        result = await template_service.get(identification)
        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize("identification", [0, "test-identifier"])
    async def test_delete__id_or_identifier_not_found(self, identification, template_service):
        """Test that the behavior is correct when the id or identifier is not found."""
        await template_service.delete(identification)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("identification_attribute", ("id", "identifier"))
    async def test_update(self, template_service, inserted_test_data, identification_attribute):
        """Test that the template is updated successfully."""
        identification = getattr(inserted_test_data, identification_attribute)

        expected_data = JobTemplateUpdateRequest(
            name="new-name",
            identifier="new-identifier",
            description=None,
            template_vars={"new_output_dir": "/tmp"},
        )

        assert JobTemplateUpdateRequest.from_orm(inserted_test_data) != expected_data

        actual_data = await template_service.update(
            identification,
            incoming_data=expected_data,
        )

        assert JobTemplateUpdateRequest.from_orm(actual_data) == expected_data
