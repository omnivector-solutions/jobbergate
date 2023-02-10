import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import buzz

from jobbergate_cli.end_to_end_testing.base import BaseEntity
from jobbergate_cli.end_to_end_testing.constants import APPLICATIONS_CACHE_PATH, TEST_APPLICATIONS_PATH
from jobbergate_cli.end_to_end_testing.utils import cached_run, get_set_of_ids


def get_application_list() -> List[Path]:
    return [p for p in TEST_APPLICATIONS_PATH.iterdir() if p.is_dir()]


def get_test_applications() -> List[Path]:
    return list((APPLICATIONS_CACHE_PATH / "create").glob("*.json"))


@dataclass
class Applications(BaseEntity):
    base_applications: List = field(default_factory=get_application_list)

    def create(self):
        for app in self.base_applications:
            identifier = f"{Path.cwd().name}-{app.name}"
            result = cached_run(
                "create-application",
                "--name",
                app.name,
                "--identifier",
                identifier,
                "--application-path",
                app.as_posix(),
                cache_path=APPLICATIONS_CACHE_PATH / "create" / f"{app.name}.json",
            )

            buzz.require_condition(
                result.get("application_uploaded") is True,
                f"Application {app.name} was not updated properly",
            )

    def get(self):
        for app in get_test_applications():
            app_data = json.loads(app.read_text())
            app_data.pop("updated_at")

            id_value = str(app_data["id"])

            result = cached_run(
                "get-application",
                "--id",
                id_value,
                cache_path=APPLICATIONS_CACHE_PATH / "get" / app.name,
            )

            with buzz.check_expressions(
                f"get-application returned unexpected data for --id={id_value}",
            ) as check:
                for key, value in app_data.items():
                    check(
                        result[key] == value,
                        f"field={key}, expected={value}, actual={result[key]}",
                    )

    def update(self):
        description = "jobbergate-cli-end-to-end-tests"
        for app in get_test_applications():
            app_data = json.loads(app.read_text())
            app_data.pop("updated_at")

            id_value = str(app_data["id"])

            result = cached_run(
                "update-application",
                "--id",
                id_value,
                "--application-desc",
                description,
                cache_path=APPLICATIONS_CACHE_PATH / "update" / app.name,
            )

            buzz.require_condition(
                result.get("application_description") == description,
                f"Application {app.name} was not updated properly",
            )

    def list(self):
        expected_ids = get_set_of_ids(get_test_applications())

        actual_result = cached_run(
            "list-applications",
            "--user",
            "--sort-field",
            "id",
            "--sort-order",
            "ASCENDING",
            cache_path=APPLICATIONS_CACHE_PATH / "list.json",
        )
        actual_ids = {i["id"] for i in actual_result}

        buzz.require_condition(
            expected_ids.issubset(actual_ids),
            f"Expected_ids={expected_ids} is not a subset of actual_ids={actual_ids}",
        )
