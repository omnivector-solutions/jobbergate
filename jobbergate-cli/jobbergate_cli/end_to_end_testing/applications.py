import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import buzz

from jobbergate_cli.end_to_end_testing.base import BaseEntity
from jobbergate_cli.end_to_end_testing.constants import APPLICATIONS_CACHE_PATH, TEST_APPLICATIONS_PATH
from jobbergate_cli.end_to_end_testing.utils import cached_run


def get_application_list() -> List[Path]:
    return [p for p in TEST_APPLICATIONS_PATH.iterdir() if p.is_dir()]


def get_test_applications() -> List[Path]:
    return list(APPLICATIONS_CACHE_PATH.glob("*.json"))


@dataclass
class Applications(BaseEntity):
    base_applications: List = field(default_factory=get_application_list)

    def create(self):
        for app in self.base_applications:
            name = app.name
            identifier = str(Path.cwd().name) + "-" + name
            cached_run(
                "create-application",
                "--name",
                name,
                "--identifier",
                identifier,
                "--application-path",
                str(app),
                "--application-desc",
                "jobbergate-cli-end-to-end-tests",
                cache_path=APPLICATIONS_CACHE_PATH / f"{app.name}.json",
            )

    def get(self):
        for app in get_test_applications():
            app_data = json.loads(app.read_text())
            app_data.pop("updated_at")
            for id_key, id_value in {
                "--id": app_data["id"],
                "--identifier": app_data["application_identifier"],
            }.items():
                result = cached_run(
                    "get-application",
                    id_key,
                    str(id_value),
                )

                with buzz.check_expressions(
                    "get-application returned unexpected data for {}={}".format(
                        id_key,
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
                get_test_applications(),
            ),
        )

        actual_result = cached_run(
            "list-applications",
            "--user",
            "--sort-field",
            "id",
            "--sort-order",
            "ASCENDING",
        )
        actual_ids = {i["id"] for i in actual_result}

        assert expected_ids.issubset(actual_ids)
