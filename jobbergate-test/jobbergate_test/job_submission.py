import json
from pathlib import Path
from typing import List

import buzz

from jobbergate_test.base import BaseEntity
from jobbergate_test.constants import JOB_SUBMISSIONS_CACHE_PATH
from jobbergate_test.job_scripts import get_test_job_scripts
from jobbergate_test.utils import cached_run, get_set_of_ids


def get_test_job_submissions() -> List[Path]:
    return list((JOB_SUBMISSIONS_CACHE_PATH / "create").glob("*.json"))


class JobSubmissions(BaseEntity):
    def create(self):
        for app in get_test_job_scripts():
            app_data = json.loads(app.read_text())
            name = app_data["job_script_name"]
            result = cached_run(
                "create-job-submission",
                "--name",
                name,
                "--job-script-id",
                str(app_data["id"]),
                "--description",
                "jobbergate-cli-end-to-end-tests",
                "--no-download",
                cache_path=JOB_SUBMISSIONS_CACHE_PATH / "create" / f"{name}.json",
            )

            buzz.require_condition(
                result.get("job_script_id") == app_data["id"],
                "The job-script-id is not the same as the one in the job-script",
            )

    def get(self):
        for app in get_test_job_submissions():
            app_data = json.loads(app.read_text())

            id_value = str(app_data["id"])

            result = cached_run(
                "get-job-submission",
                "--id",
                id_value,
                cache_path=JOB_SUBMISSIONS_CACHE_PATH / "get" / app.name,
            )

            with buzz.check_expressions(
                "get-job-submission returned unexpected data for --id={}".format(
                    id_value,
                )
            ) as check:
                app_data.pop("status")
                app_data.pop("updated_at")
                app_data.pop("slurm_job_id")
                app_data.pop("report_message")
                for key, value in app_data.items():
                    check(
                        result[key] == value,
                        f"field={key}, expected={value}, actual={result[key]}",
                    )

    def update(self):
        """
        There is no command available on the cli to update a job-submission.
        """
        pass

    def list(self):
        expected_ids = get_set_of_ids(get_test_job_submissions())

        actual_result = cached_run(
            "list-job-submissions",
            "--sort-field",
            "id",
            "--sort-order",
            "ASCENDING",
            cache_path=JOB_SUBMISSIONS_CACHE_PATH / "list.json",
        )
        actual_ids = {i["id"] for i in actual_result}

        buzz.require_condition(
            expected_ids.issubset(actual_ids),
            f"Expected_ids={expected_ids} is not a subset of actual_ids={actual_ids}",
        )
