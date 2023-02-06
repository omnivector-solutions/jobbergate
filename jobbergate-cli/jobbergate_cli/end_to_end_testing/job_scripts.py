import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import buzz

from jobbergate_cli.end_to_end_testing.applications import get_test_applications
from jobbergate_cli.end_to_end_testing.base import BaseEntity
from jobbergate_cli.end_to_end_testing.constants import JOB_SCRIPTS_CACHE_PATH
from jobbergate_cli.end_to_end_testing.utils import cached_run


def get_test_job_scripts() -> List[Path]:
    return list(JOB_SCRIPTS_CACHE_PATH.glob("*.json"))


@dataclass
class JobScripts(BaseEntity):
    base_applications: List = field(default_factory=get_test_applications)

    def create(self):
        for app in self.base_applications:
            app_data = json.loads(app.read_text())
            name = app_data["application_name"]
            cache = JOB_SCRIPTS_CACHE_PATH / f"{name}.json"
            cached_run(
                cache,
                "create-job-script",
                "--fast",
                "--name",
                name,
                "--application-identifier",
                app_data["application_identifier"],
                "--description",
                app_data["application_description"],
            )

    def get(self):
        for app in get_test_job_scripts():
            app_data = json.loads(app.read_text())

            id_value = str(app_data["id"])

            result = cached_run(None, "get-job-script", "--id", str(id_value))

            with buzz.check_expressions(
                "get-job-script returned unexpected data for --if={}".format(
                    id_value,
                )
            ) as check:
                for key, value in app_data.items():
                    check(
                        result[key] == value,
                        f"field={key}, expected={value}, actual={result[key]}",
                    )

    def list(self):
        expected_ids = set(
            map(
                lambda app: json.loads(app.read_text())["id"],
                get_test_job_scripts(),
            ),
        )

        actual_result = cached_run(
            None,
            "list-job-scripts",
            "--sort-field",
            "id",
            "--sort-order",
            "ASCENDING",
        )
        actual_ids = {i["id"] for i in actual_result}

        assert expected_ids.issubset(actual_ids)
