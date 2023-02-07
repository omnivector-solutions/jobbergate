import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import buzz

from jobbergate_cli.end_to_end_testing.base import BaseEntity
from jobbergate_cli.end_to_end_testing.constants import JOB_SUBMISSIONS_CACHE_PATH
from jobbergate_cli.end_to_end_testing.job_scripts import get_test_job_scripts
from jobbergate_cli.end_to_end_testing.utils import cached_run


def get_test_job_submissions() -> List[Path]:
    return list(JOB_SUBMISSIONS_CACHE_PATH.glob("*.json"))


@dataclass
class JobSubmissions(BaseEntity):
    base_applications: List = field(default_factory=get_test_job_scripts)

    def create(self):
        for app in self.base_applications:
            app_data = json.loads(app.read_text())
            name = app_data["job_script_name"]
            cached_run(
                "create-job-submission",
                "--name",
                name,
                "--job-script-id",
                str(app_data["id"]),
                "--description",
                app_data["job_script_description"],
                "--no-download",
                cache_path=JOB_SUBMISSIONS_CACHE_PATH / f"{name}.json",
            )

    def get(self):
        for app in get_test_job_submissions():
            app_data = json.loads(app.read_text())

            id_value = str(app_data["id"])

            result = cached_run("get-job-submission", "--id", str(id_value))

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

    def list(self):
        expected_ids = set(
            map(
                lambda app: json.loads(app.read_text())["id"],
                get_test_job_submissions(),
            ),
        )

        actual_result = cached_run(
            "list-job-submissions",
            "--sort-field",
            "id",
            "--sort-order",
            "ASCENDING",
        )
        actual_ids = {i["id"] for i in actual_result}

        assert expected_ids.issubset(actual_ids)
