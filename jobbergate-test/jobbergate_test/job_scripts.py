import json
from pathlib import Path
from typing import List

import buzz

from jobbergate_cli.end_to_end_testing.applications import get_test_applications
from jobbergate_cli.end_to_end_testing.base import BaseEntity
from jobbergate_cli.end_to_end_testing.constants import JOB_SCRIPTS_CACHE_PATH
from jobbergate_cli.end_to_end_testing.utils import cached_run, get_set_of_ids


def get_test_job_scripts() -> List[Path]:
    return list((JOB_SCRIPTS_CACHE_PATH / "create").glob("*.json"))


class JobScripts(BaseEntity):
    def create(self):
        for app in get_test_applications():
            app_data = json.loads(app.read_text())
            name = app_data["application_name"]
            result = cached_run(
                "create-job-script",
                "--no-submit",
                "--fast",
                "--name",
                name,
                "--application-identifier",
                app_data["application_identifier"],
                cache_path=JOB_SCRIPTS_CACHE_PATH / "create" / f"{name}.json",
            )

            buzz.require_condition(
                result.get("application_id") == app_data["id"],
                "The application id is not the same as the one in the application",
            )

    def get(self):
        for app in get_test_job_scripts():
            app_data = json.loads(app.read_text())

            id_value = str(app_data["id"])

            result = cached_run(
                "get-job-script",
                "--id",
                id_value,
                cache_path=JOB_SCRIPTS_CACHE_PATH / "get" / app.name,
            )

            with buzz.check_expressions(
                f"get-job-script returned unexpected data for --id={id_value}",
            ) as check:
                for key, value in app_data.items():
                    check(
                        result[key] == value,
                        f"field={key}, expected={value}, actual={result[key]}",
                    )

    def update(self):
        description = "jobbergate-cli-end-to-end-tests"
        for app in get_test_job_scripts():
            app_data = json.loads(app.read_text())
            app_data.pop("updated_at")

            id_value = str(app_data["id"])

            result = cached_run(
                "update-job-script",
                "--id",
                id_value,
                "--description",
                description,
                cache_path=JOB_SCRIPTS_CACHE_PATH / "update" / app.name,
            )

            buzz.require_condition(
                result.get("job_script_description") == description,
                f"Job-script {app.name} was not updated properly",
            )

    def list(self):
        expected_ids = get_set_of_ids(get_test_job_scripts())

        actual_result = cached_run(
            "list-job-scripts",
            "--sort-field",
            "id",
            "--sort-order",
            "ASCENDING",
            cache_path=JOB_SCRIPTS_CACHE_PATH / "list.json",
        )
        actual_ids = {i["id"] for i in actual_result}

        buzz.require_condition(
            expected_ids.issubset(actual_ids),
            f"Expected_ids={expected_ids} is not a subset of actual_ids={actual_ids}",
        )
