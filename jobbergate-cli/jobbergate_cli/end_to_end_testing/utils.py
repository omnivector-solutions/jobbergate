import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import buzz
from loguru import logger


def run(*command):
    """
    Run a command and return the result.
    """
    result = subprocess.run(
        command,
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
    command = ["jobbergate", "--raw", "--full", *args]
    logger.debug(f"Preparing command: {' '.join(command)}")

    if cache_path is not None and cache_path.is_file():
        logger.debug(f"Using cached result from: {cache_path}")
        return json.loads(cache_path.read_text())

    result = run(*command)
    result_json = json.loads(result.stdout)

    if cache_path is not None:
        logger.debug(f"Saving result to: {cache_path}")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(result_json))

    return result_json


def get_set_of_ids(list_of_paths: List[Path]) -> Set[int]:
    """
    Get a list of ids from a list of paths.
    """
    result = {json.loads(app.read_text()).get("id") for app in list_of_paths}

    buzz.require_condition(None not in result, f"Got None in the list of ids: {result}")

    return result
