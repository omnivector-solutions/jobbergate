from pathlib import Path
from dataclasses import dataclass
from typing import List

import subprocess
import json
import buzz

TEST_APPLICATIONS_PATH = Path("..", "examples")

TEST_CACHE_PATH = Path(".jobbergate_test_cache")
APPLICATIONS_CACHE_PATH = TEST_CACHE_PATH / "applications"


def run(*args):
    result = subprocess.run(
        ["jobbergate", "--raw", "--full", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        check=False,
    )

    with buzz.handle_errors(
        "Got returncode={} when running {} due to: {}".format(
            result.returncode,
            " ".join(result.args),
            result.stderr,
        )
    ):
        result.check_returncode()

    return result


def cached_run(file_path, *args):
    if file_path is not None and file_path.is_file():
        return json.loads(file_path.read_text())

    result = run(*args)
    result_json = json.loads(result.stdout)

    if file_path is not None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(result_json))

    return result_json


@dataclass
class Applications:
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


def main():

    applications = Applications(
        entity_list=[p for p in TEST_APPLICATIONS_PATH.iterdir() if p.is_dir()],
    )

    applications.create()
    applications.get()
    applications.list()
    print("main")


if __name__ == "__main__":
    main()
