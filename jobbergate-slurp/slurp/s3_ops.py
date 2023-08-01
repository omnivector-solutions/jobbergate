"""
Provides a convenience class for managing calls to S3.
"""
import asyncio
import contextlib
import itertools
import json
import re
import tarfile
import tempfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List

import aioboto3
import pydantic
import yaml
from buzz import check_expressions, handle_errors, require_condition
from loguru import logger

from slurp.config import settings

APPLICATIONS_WORK_DIR = "applications"
APPLICATION_CONFIG_FILE_NAME = "jobbergate.yaml"
APPLICATION_SOURCE_FILE_NAME = "jobbergate.py"
APPLICATION_TEMPLATE_FOLDER = "templates"


@contextlib.asynccontextmanager
async def s3_bucket(is_legacy: bool = True):
    """
    Context manager used to get a bucket from S3.

    It is connected to the legacy bucket when is_legacy is True, otherwise,
    it is connected to the nextgen bucket.
    """

    if is_legacy:
        endpoint_url = settings.LEGACY_S3_ENDPOINT_URL
        bucket_name = settings.LEGACY_S3_BUCKET_NAME
        key_id = settings.LEGACY_AWS_ACCESS_KEY_ID
        access_key = settings.LEGACY_AWS_SECRET_ACCESS_KEY
    else:
        endpoint_url = settings.NEXTGEN_S3_ENDPOINT_URL
        bucket_name = settings.NEXTGEN_S3_BUCKET_NAME
        key_id = settings.NEXTGEN_AWS_ACCESS_KEY_ID
        access_key = settings.NEXTGEN_AWS_SECRET_ACCESS_KEY

    session = aioboto3.Session(aws_access_key_id=key_id, aws_secret_access_key=access_key)

    async with session.resource("s3", endpoint_url=endpoint_url) as s3:
        bucket = await s3.Bucket(bucket_name)
        yield bucket


@contextlib.contextmanager
def extract_tarball(legacy_object):
    """
    Extract the files in the tarball to a temporary directory.

    Its path is yielded for reference. The directory is deleted after the context manager is closed.
    """

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with tarfile.open(fileobj=BytesIO(legacy_object), mode="r:gz") as tar:
            tar.extractall(tmp_path)

        yield tmp_path


legacy_key_pattern = r"^{}[/](?P<user_id>\d+)[/]{}[/](?P<application_id>\d+)[/]{}$".format(
    "jobbergate-resources",
    "applications",
    "jobbergate.tar.gz",
)
legacy_key_compiled = re.compile(legacy_key_pattern)


def get_id_from_legacy_s3_key(key: str) -> int:
    """
    Get the application id from a given key at the legacy bucket.

    The key is expected to be in the format:
        jobbergate-resources/<user_id>/applications/<application_id>/jobbergate.tar.gz
    where <user_id> and <application_id> are integers.
    """

    match = legacy_key_compiled.match(key)

    require_condition(
        match is not None,
        f"No match was found for application-id and user-id and: {key}",
    )

    return int(match.group("application_id"))


def check_application_files(work_dir: Path):
    """
    Check if the required files are present in the application directory.

    It includes:
        - jobbergate.yaml
        - jobbergate.py
        - One or more jinja templates
    """
    with check_expressions(
        f"Check on application files failed, the available files are: {[f.as_posix() for f in work_dir.rglob('*')]}"
    ) as check:
        for file in [APPLICATION_CONFIG_FILE_NAME, APPLICATION_SOURCE_FILE_NAME]:
            check((work_dir / file).is_file(), f"File {file} was not found")

        template_files = itertools.chain(work_dir.rglob("*.j2"), work_dir.rglob("*.jinja2"))

        check(len(list(template_files)) >= 1, "No template file was found")


class JobbergateApplicationConfig(pydantic.BaseModel):
    """
    A data object describing the config data needed to instantiate a JobbergateApplication class.
    """

    application_config: Dict[str, Any]
    jobbergate_config: Dict[str, Any]


def load_application_config_from_source(config_source_path: Path) -> JobbergateApplicationConfig:
    """
    Load the JobbergateApplicationConfig from a text string containing the config as YAML.

    :param: config_source: The YAML containing the config
    :returns: A JobbergateApplicationConfig instance with the config values
    """
    config_data = yaml.safe_load(config_source_path.read_text())
    config = JobbergateApplicationConfig(**config_data)
    return config


def get_key(table_name: str, parent_id: int, filename: str) -> str:
    return f"{table_name}/{parent_id}/{filename}"


async def transfer_application_files(legacy_applications, db) -> List[int]:
    """
    Transfer the application files from the legacy bucket to the nextgen bucket.
    """
    logger.info("Start migrating application files to s3")

    legacy_application_ids = {application["id"] for application in legacy_applications}

    async def transfer_helper(s3_object, nextgen_bucket):
        """
        Helper function that transfers the files from one entry at the legacy bucket to the nextgen bucket.
        """
        id = get_id_from_legacy_s3_key(s3_object.key)

        require_condition(
            id in legacy_application_ids,
            f"Missing application id (files on S3 but id not on the database): {s3_object.key}",
        )

        with handle_errors(f"Error retrieving object from legacy bucket: {s3_object.key}"):
            s3_legacy_object = await s3_object.get()
            s3_legacy_content = await s3_legacy_object["Body"].read()

        with handle_errors(f"Error manipulating the files from: {s3_object.key}"):
            with extract_tarball(s3_legacy_content) as work_dir:
                check_application_files(work_dir)

                application_config = load_application_config_from_source(
                    work_dir / APPLICATION_CONFIG_FILE_NAME
                )

                with db(is_legacy=False) as nextgen_db:
                    nextgen_db.execute(
                        """
                        update job_script_templates
                        set template_vars = %s
                        where id = %s
                        """,
                        (
                            json.dumps(application_config.application_config),
                            id,
                        ),
                    )

                    nextgen_db.execute(
                        """
                        insert into workflow_files (
                            parent_id,
                            runtime_config,
                            filename,
                            created_at,
                            updated_at
                        )
                        values (%s, %s, %s, %s, %s)
                        """,
                        (
                            id,
                            json.dumps(application_config.jobbergate_config),
                            APPLICATION_SOURCE_FILE_NAME,
                            datetime.now(timezone.utc),
                            datetime.now(timezone.utc),
                        ),
                    )

                    await nextgen_bucket.upload_file(
                        work_dir / APPLICATION_SOURCE_FILE_NAME,
                        get_key("workflow_files", id, APPLICATION_SOURCE_FILE_NAME),
                    )

                    supporting_files = application_config.jobbergate_config.get("supporting_files", [])

                    for complete_template_path in itertools.chain(
                        work_dir.rglob("*.j2"), work_dir.rglob("*.jinja2")
                    ):
                        relative_template_path = complete_template_path.relative_to(work_dir)

                        if relative_template_path.as_posix() in supporting_files:
                            file_type = "SUPPORT"
                        else:
                            file_type = "ENTRYPOINT"

                        nextgen_db.execute(
                            """
                            insert into job_script_template_files (
                            parent_id,
                            file_type,
                            filename,
                            created_at,
                            updated_at
                            )
                            values (%s, %s, %s, %s, %s)
                            """,
                            (
                                id,
                                file_type,
                                relative_template_path.as_posix(),
                                datetime.now(timezone.utc),
                                datetime.now(timezone.utc),
                            ),
                        )

                        await nextgen_bucket.upload_file(
                            complete_template_path,
                            get_key("job_script_templates", id, relative_template_path.as_posix()),
                        )

            return id

    async with s3_bucket(is_legacy=True) as legacy_bucket:
        async with s3_bucket(is_legacy=False) as nextgen_bucket:
            prefix = "jobbergate-resources/"

            tasks = [
                asyncio.create_task(transfer_helper(s3_object, nextgen_bucket))
                async for s3_object in legacy_bucket.objects.filter(Prefix=prefix)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

    transferred_ids = set()
    for r in results:
        if isinstance(r, Exception):
            logger.warning(str(r))
        elif isinstance(r, int):
            transferred_ids.add(r)
        else:
            logger.error("Unexpected result: {} {}".format(type(r), r))

    logger.success(f"Finished migrating {len(transferred_ids)} applications to s3")
    missing_ids = legacy_application_ids - transferred_ids
    if missing_ids:
        logger.warning(f"Missing files for application ids (total={len(missing_ids)}): {missing_ids}")

    return list(transferred_ids)
