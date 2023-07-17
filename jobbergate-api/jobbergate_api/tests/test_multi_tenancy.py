"""
Test the multitenancy logic for Jobbergate API.
"""

from contextlib import asynccontextmanager
from typing import Optional
from unittest.mock import patch

import asyncpg
import pytest
from fastapi import status

from jobbergate_api.apps.applications.application_files import ApplicationFiles
from jobbergate_api.apps.applications.models import applications_table
from jobbergate_api.apps.applications.schemas import ApplicationPartialResponse
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.config import settings
from jobbergate_api.metadata import metadata
from jobbergate_api.storage import engine_factory, fetch_count, fetch_instance, insert_data


@pytest.fixture(autouse=True, scope="module")
async def alt_engine():
    """
    Provide a fixture to prepare the alternative test database.

    Note that we DO NOT cleanup the engine factory in this fixture. The main fixture will cover this.
    """
    engine = engine_factory.get_engine("alt-test-db")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(metadata.create_all, checkfirst=True)
        try:
            yield engine
        finally:
            async with engine.begin() as connection:
                for table in reversed(metadata.sorted_tables):
                    await connection.execute(table.delete())
    except asyncpg.exceptions.InvalidCatalogNameError:
        pytest.skip(
            "Skipping multi-tenancy tests as alternative test database is not available",
            allow_module_level=True,
        )


@pytest.fixture(scope="function")
def get_synth_sessions():
    """
    Get a the default and alternat sessions from the engine_factory.

    This method produces a session for both the default and alternate test database.

    This is necessary to make sure that the test code uses the same session as the one returned by
    the dependency injection for the router code. Otherwise, changes made in the router's session would not
    be visible in the test code. Not that changes made in this synthesized session are always rolled back
    and never committed.

    If multi-tenancy is enabled, the override_db_name for the default session will be the name of the normal
    test database.
    """

    @asynccontextmanager
    async def helper():
        default_session = engine_factory.get_session()
        await default_session.begin_nested()

        alt_session = engine_factory.get_session("alt-test-db")
        await alt_session.begin_nested()

        def _get_session(override_db_name: Optional[str] = None):
            if override_db_name is None or override_db_name == settings.TEST_DATABASE_NAME:
                return default_session
            elif override_db_name == "alt-test-db":
                return alt_session
            else:
                raise RuntimeError(f"Unknown test database name: {override_db_name}")

        with patch("jobbergate_api.storage.engine_factory.get_session", side_effect=_get_session):
            yield (default_session, alt_session)

        await default_session.rollback()
        await default_session.close()

        await alt_session.rollback()
        await alt_session.close()

    return helper


@pytest.mark.asyncio
async def test_get_session():
    """
    Test that a different session is fetched from ``get_session()`` when supplying ``override_db_name``.

    Requires that the test database server is running a second test database named "alt-test-db".
    """
    default_session = None
    alt_session = None
    try:
        default_session = engine_factory.get_session()
        alt_session = engine_factory.get_session("alt-test-db")
        assert default_session is not alt_session

    finally:
        if default_session:
            await default_session.close()
        if alt_session:
            await alt_session.close()


@pytest.mark.asyncio
async def test_session_tenancy(get_synth_sessions):
    """
    Test tenancy with the database sessions produced by the engine_factory's ``get_session()`` helper.

    Checks that database writes and reads for the two sessions are distinct and do not effect each other.
    """
    async with get_synth_sessions() as (default_session, alt_session):
        application_data = dict(
            application_owner_email="test@email.com",
            application_name="test_name",
        )
        default_id = await insert_data(default_session, applications_table, application_data)
        alt_id = await insert_data(alt_session, applications_table, application_data)

        assert await fetch_count(default_session, applications_table) == 1
        assert await fetch_count(alt_session, applications_table) == 1

        default_instance = fetch_instance(
            default_session, default_id, applications_table, ApplicationPartialResponse
        )
        alt_instance = fetch_instance(alt_session, alt_id, applications_table, ApplicationPartialResponse)

        assert default_instance is not alt_instance


@pytest.mark.asyncio
async def test_application_router__create_with_multi_tenancy(
    get_synth_sessions,
    client,
    inject_security_header,
    tweak_settings,
):
    """
    Test POST /applications/ correctly creates an application using multi-tenancy.

    This method checks to make sure that the correct database is used for the API request based on the
    organization_id that is provided in the auth token in the request header.
    """
    default_organization_id = settings.TEST_DATABASE_NAME
    alt_organization_id = "alt-test-db"

    with tweak_settings(MULTI_TENANCY_ENABLED=True):
        async with get_synth_sessions() as (default_session, alt_session):

            inject_security_header(
                "default@email.com", Permissions.APPLICATIONS_EDIT, organization_id=default_organization_id
            )
            response = await client.post(
                "/jobbergate/applications/",
                json=dict(
                    application_owner_email="default@email.com",
                    application_name="default-application",
                ),
            )

            assert response.status_code == status.HTTP_201_CREATED
            default_response_application = ApplicationPartialResponse(**response.json())
            assert default_response_application.application_name == "default-application"

            default_database_application = await fetch_instance(
                default_session,
                default_response_application.id,
                applications_table,
                ApplicationPartialResponse,
            )
            assert default_database_application == default_response_application

            inject_security_header(
                "alt@email.com", Permissions.APPLICATIONS_EDIT, organization_id=alt_organization_id
            )
            response = await client.post(
                "/jobbergate/applications/",
                json=dict(
                    application_owner_email="alt@email.com",
                    application_name="alt-application",
                ),
            )

            assert response.status_code == status.HTTP_201_CREATED
            alt_response_application = ApplicationPartialResponse(**response.json())
            assert alt_response_application.application_name == "alt-application"

            alt_database_application = await fetch_instance(
                alt_session,
                alt_response_application.id,
                applications_table,
                ApplicationPartialResponse,
            )
            assert alt_database_application == alt_response_application


@pytest.mark.asyncio
async def test_application_router__upload_file_with_multi_tenancy(
    get_synth_sessions,
    client,
    inject_security_header,
    tweak_settings,
    make_dummy_file,
    dummy_application_config,
    make_files_param,
):
    """
    Test that files are uploaded correctly using using multi-tenancy.

    This method checks to make sure that the correct bucket name is used for the API request based on the
    organization_id that is provided in the auth token in the request header.
    """
    default_organization_id = settings.TEST_DATABASE_NAME
    alt_organization_id = "alt-test-db"

    dummy_file = make_dummy_file("jobbergate.yaml", content=dummy_application_config)

    with tweak_settings(
        MULTI_TENANCY_ENABLED=True,
        MAX_UPLOAD_FILE_SIZE=600,
    ):
        with make_files_param(dummy_file) as files_param:
            async with get_synth_sessions() as (default_session, alt_session):

                with patch(
                    "jobbergate_api.apps.applications.routers.ApplicationFiles.get_from_upload_files",
                    return_value=ApplicationFiles(),
                ):
                    with patch(
                        "jobbergate_api.apps.applications.routers.ApplicationFiles.write_to_s3"
                    ) as mocked_uploader:

                        default_application_data = dict(
                            application_owner_email="default@email.com",
                            application_name="default_name",
                        )

                        default_inserted_id = await insert_data(
                            default_session,
                            applications_table,
                            default_application_data,
                        )
                        assert await fetch_count(default_session, applications_table) == 1

                        default_application = await fetch_instance(
                            default_session,
                            default_inserted_id,
                            applications_table,
                            ApplicationPartialResponse,
                        )
                        assert not default_application.application_uploaded

                        inject_security_header(
                            "default@email.com",
                            Permissions.APPLICATIONS_EDIT,
                            organization_id=default_organization_id,
                        )

                        response = await client.post(
                            f"/jobbergate/applications/{default_inserted_id}/upload",
                            files=files_param,
                        )

                        assert response.status_code == status.HTTP_201_CREATED
                        mocked_uploader.assert_called_once_with(
                            default_inserted_id, override_bucket_name=default_organization_id
                        )

                with patch(
                    "jobbergate_api.apps.applications.routers.ApplicationFiles.get_from_upload_files",
                    return_value=ApplicationFiles(),
                ):
                    with patch(
                        "jobbergate_api.apps.applications.routers.ApplicationFiles.write_to_s3"
                    ) as mocked_uploader:

                        alt_application_data = dict(
                            application_owner_email="alt@email.com",
                            application_name="alt_name",
                        )

                        alt_inserted_id = await insert_data(
                            alt_session,
                            applications_table,
                            alt_application_data,
                        )
                        assert await fetch_count(alt_session, applications_table) == 1

                        alt_application = await fetch_instance(
                            alt_session, alt_inserted_id, applications_table, ApplicationPartialResponse
                        )
                        assert not alt_application.application_uploaded

                        inject_security_header(
                            "alt@email.com",
                            Permissions.APPLICATIONS_EDIT,
                            organization_id=alt_organization_id,
                        )
                        response = await client.post(
                            f"/jobbergate/applications/{alt_inserted_id}/upload",
                            files=files_param,
                        )

                        assert response.status_code == status.HTTP_201_CREATED
                        mocked_uploader.assert_called_once_with(
                            alt_inserted_id, override_bucket_name=alt_organization_id
                        )
