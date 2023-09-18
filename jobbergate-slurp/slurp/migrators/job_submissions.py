"""
Provides logic for migrating job_submission data from legacy db to nextgen db.
"""
from loguru import logger

from slurp.batch import batch


def migrate_job_submissions(nextgen_db, legacy_job_submissions, user_map, batch_size=1000):
    """
    Inserts job_submission data to nextgen database.

    Given a list of legacy job_submissions, a user map, and a job_script map, create
    records in the nextgen database for each job_submission.
    """
    logger.info("Migrating job_submissions to nextgen database")

    def _slurm_job_id(old_id):
        """
        Just a dumb function that safely converts the old slurm id to an int.
        """
        try:
            return int(old_id)
        except ValueError:
            return None

    for job_submission_batch in batch(legacy_job_submissions, batch_size):
        mogrified_params = ",".join(
            [
                nextgen_db.mogrify(
                    """
                    (
                        %(id)s,
                        %(name)s,
                        %(description)s,
                        %(owner_email)s,
                        %(job_script_id)s,
                        %(slurm_job_id)s,
                        %(created)s,
                        %(updated)s,
                        %(status)s,
                        %(client_id)s
                    )
                    """,
                    dict(
                        id=job_submission["id"],
                        name=job_submission["job_submission_name"],
                        description=job_submission["job_submission_description"],
                        owner_email=user_map[job_submission["job_submission_owner_id"]]["email"],
                        job_script_id=job_submission["job_script_id"],
                        slurm_job_id=_slurm_job_id(job_submission["slurm_job_id"]),
                        created=job_submission["created_at"],
                        updated=job_submission["updated_at"],
                        status="UNKNOWN",
                        client_id="unknown",
                    ),
                )
                for job_submission in job_submission_batch
            ]
        )

        nextgen_db.execute(
            """
            insert into job_submissions (
                id,
                name,
                description,
                owner_email,
                job_script_id,
                slurm_job_id,
                created_at,
                updated_at,
                status,
                client_id
            )
            values {}
            on conflict do nothing
            """.format(
                mogrified_params
            )
        )

    logger.success("Finished migrating job_submissions")
