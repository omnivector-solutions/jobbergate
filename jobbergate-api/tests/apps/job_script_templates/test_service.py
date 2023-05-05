"""Database models for the smart template resource."""
from io import BytesIO
from typing import Any
from fastapi import UploadFile

import pytest
from aioboto3.session import Session as Boto3Session
from sqlalchemy.exc import IntegrityError, NoResultFound
from jobbergate_api.apps.constants import FileType

from jobbergate_api.apps.job_script_templates.models import JobScriptTemplate
from jobbergate_api.apps.job_script_templates.schemas import (
    JobTemplateCreateRequest,
    JobTemplateUpdateRequest,
)
from jobbergate_api.apps.job_script_templates.service import (
    JobScriptTemplateFilesService,
    JobScriptTemplateService,
)
from jobbergate_api.config import settings
from jobbergate_api.database import SessionLocal

# Force the async event loop at the app to begin.
# Since this is a time consuming fixture, it is just used where strict necessary.
# pytestmark = pytest.mark.usefixtures("startup_event_force")


@pytest.fixture
async def db_session():
    """Return the database session."""
    async with SessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def template_service(db_session):
    """Return the services module."""
    yield JobScriptTemplateService(session=db_session)


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
        with pytest.raises(NoResultFound):
            await template_service.delete(identification)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("identification_attribute", ("id", "identifier"))
    async def test_update__success(self, template_service, inserted_test_data, identification_attribute):
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

    @pytest.mark.asyncio
    @pytest.mark.parametrize("identification", [0, "test-identifier"])
    async def test_update__not_found(self, identification, template_service):
        """Test that the template is updated successfully."""

        update_data = JobTemplateUpdateRequest(
            name="new-name",
            identifier="new-identifier",
            description=None,
            template_vars={"new_output_dir": "/tmp"},
        )

        with pytest.raises(NoResultFound):
            await template_service.update(
                id_or_identifier=identification,
                incoming_data=update_data,
            )


@pytest.fixture
async def template_files_service(db_session):
    """Return the services module."""
    s3_session = Boto3Session()
    async with s3_session.resource(
        "s3",
        endpoint_url="http://localhost:9000",
        aws_access_key_id="compose-s3-key",
        aws_secret_access_key="compose-s3-secret",
    ) as s3:
        bucket = await s3.Bucket("jobbergate-resources")
        yield JobScriptTemplateFilesService(session=db_session, bucket=bucket)


# class TestTemplateFilesService:
#     @pytest.mark.asyncio
#     def test_object_is_valid(self, template_files_service):
#         """Test that the object is valid."""
#         assert isinstance(template_files_service, JobScriptTemplateFilesService)

#     @pytest.mark.asyncio
#     async def test_add_file__end_to_end(self, template_files_service, inserted_test_data, tmp_path):
#         """Test that the file is added successfully."""
#         file_name = "test.txt"
#         file_content = "test"
#         file_type = FileType.ENTRYPOINT

#         file_path = tmp_path / file_name
#         file_path.write_text(file_content)
#         with open(file_path, "rb") as f:
#             template_file = await template_files_service.upsert(
#                 job_script_template_id=inserted_test_data.id,
#                 file_type=file_type,
#                 upload_file=UploadFile(f, filename=file_path.name),
#             )

#         assert template_file.id == inserted_test_data.id
#         assert template_file.file_type == file_type
#         assert template_file.filename == file_name

#         fileobj = await template_files_service.get(template_file)

#         assert await fileobj["Body"].read() == file_content.encode()

#         await template_files_service.delete(template_file)

#         with pytest.raises(Exception):
#             await template_files_service.get(template_file)
