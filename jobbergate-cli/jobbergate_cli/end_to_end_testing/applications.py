from pathlib import Path
from dataclasses import dataclass
from typing import List
from jobbergate_cli.end_to_end_testing.constants import APPLICATIONS_CACHE_PATH
from jobbergate_cli.end_to_end_testing.utils import cached_run
from jobbergate_cli.end_to_end_testing.base import BaseEntity

import json
import buzz


@dataclass
class Applications(BaseEntity):
    entity_list: List

    def create(self):
        for app in self.entity_list:
            cache = APPLICATIONS_CACHE_PATH / f"{app.name}.json"
            name = app.name
            identifier = str(Path.cwd().name) + "-" + name
            cached_run(
                cache,
                "create-application",
                "--name",
                name,
                "--identifier",
                identifier,
                "--application-path",
                str(app),
                "--application-desc",
                "jobbergate-cli-end-to-end-tests",
            )

    def get(self):
        for app in APPLICATIONS_CACHE_PATH.glob("*.json"):
            app_data = json.loads(app.read_text())
            app_data.pop("updated_at")
            for id_key, id_value in {
                "--id": app_data["id"],
                "--identifier": app_data["application_identifier"],
            }.items():
                result = cached_run(
                    None,
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
                APPLICATIONS_CACHE_PATH.glob("*.json"),
            ),
        )

        actual_result = cached_run(
            None,
            "list-applications",
            "--user",
            "--sort-field",
            "id",
            "--sort-order",
            "ASCENDING",
        )
        actual_ids = {i["id"] for i in actual_result}

        assert expected_ids.issubset(actual_ids)
