import json
import subprocess

import buzz


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
