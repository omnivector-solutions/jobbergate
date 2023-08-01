"""
Provides logic for migrating job_script data from legacy db to nextgen db.
"""

import asyncio
from io import BytesIO
import json
from buzz import handle_errors, require_condition

from loguru import logger

from slurp.batch import batch
from slurp.s3_ops import s3_bucket


def migrate_job_scripts(nextgen_db, legacy_job_scripts, user_map, batch_size=1000):
    """
    Inserts job_script data to nextgen database.

    Given a list of legacy job_scripts, a user map, and an application map, create
    records in the nextgen database for each job_script.
    """
    logger.info("Migrating job_scripts to nextgen database")

    for job_script_batch in batch(legacy_job_scripts, batch_size):
        mogrified_params = ",".join(
            [
                nextgen_db.mogrify(
                    """
                    (
                        %(id)s,
                        %(name)s,
                        %(description)s,
                        %(owner_email)s,
                        %(application_id)s,
                        %(created)s,
                        %(updated)s
                    )
                    """,
                    dict(
                        id=job_script["id"],
                        name=job_script["job_script_name"],
                        description=job_script["job_script_description"],
                        owner_email=user_map[job_script["job_script_owner_id"]]["email"],
                        application_id=job_script["application_id"],
                        created=job_script["created_at"],
                        updated=job_script["updated_at"],
                    ),
                )
                for job_script in job_script_batch
            ]
        )

        nextgen_db.execute(
            """
            insert into job_scripts (
                id,
                name,
                description,
                owner_email,
                parent_template_id,
                created_at,
                updated_at
            )
            values {}
            """.format(
                mogrified_params
            ),
        )

    logger.success("Finished migrating job_scripts")


async def transfer_job_script_files(legacy_job_scripts, batch_size=400):
    """
    Transfer job-script files from a column in the legacy database to nextgen s3.
    """
    logger.info("Start migrating job-script files to s3")

    main_filename = "application.sh"
    s3_key_template = f"job-scripts/{{job_script_id}}/main-file/{main_filename}"

    async def transfer_helper(bucket, job_script_data_as_string, job_script_id):
        """
        Helper function that handles the transfer of a single job-script.
        """
        with handle_errors(
            f"Error getting the job-script content from the JSON ({job_script_id=}): {job_script_data_as_string}"
        ):
            unpacked_data = json.loads(job_script_data_as_string)
            job_script_content = unpacked_data[main_filename]

        require_condition(bool(job_script_content), f"Empty job script content for {job_script_id=}")

        s3_key = s3_key_template.format(job_script_id=job_script_id)

        with handle_errors(f"Error uploading {job_script_id=} content to {s3_key=}"):
            await bucket.upload_fileobj(BytesIO(job_script_content.encode("utf-8")), s3_key)

        return job_script_id

    transferred_ids = set()
    async with s3_bucket(is_legacy=False) as bucket:
        for job_script_batch in batch(legacy_job_scripts, batch_size):
            tasks = (
                asyncio.create_task(
                    transfer_helper(bucket, job_script["job_script_data_as_string"], job_script["id"])
                )
                for job_script in job_script_batch
            )

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    logger.warning(str(r))
                elif isinstance(r, int):
                    transferred_ids.add(r)
                else:
                    logger.error(
                        "Unexpected result for job_script_id={}: {} {}".format(
                            job_script_batch[i]["id"], type(r), r
                        )
                    )

    logger.success(f"Finished migrating {len(transferred_ids)} job-script files to s3")
