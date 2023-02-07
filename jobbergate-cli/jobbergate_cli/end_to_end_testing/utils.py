import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

import buzz


def run(*args):
    """
    Run a jobbergate command and return the result.
    """
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


def cached_run(*args, cache_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Run a jobbergate command and cache the result if cache_path is specified.

    It the cache file exists, it will be returned instead of running the command.
    """
    if cache_path is not None and cache_path.is_file():
        return json.loads(cache_path.read_text())

    result = run(*args)
    result_json = json.loads(result.stdout)

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(result_json))

    return result_json
