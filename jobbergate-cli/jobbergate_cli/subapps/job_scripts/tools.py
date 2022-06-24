"""
Provide tool functions for working with Job Script data
"""

import json
import pathlib
from typing import Any, Dict, cast

from jobbergate_cli.exceptions import Abort
from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import JobbergateContext, JobScriptResponse


def validate_parameter_file(parameter_path: pathlib.Path) -> Dict[str, Any]:
    """
    Validate parameter file at the supplied path and returns the parsed dict.

    Confirms:
        parameter_path exists
        parameter_path is a valid json file
    """
    data = None
    with Abort.check_expressions(
        f"The parameter file at {parameter_path} was invalid",
        raise_kwargs=dict(
            subject="Invalid parameter file",
            log_message=f"Parameter file located at {parameter_path} failed validation",
        ),
    ) as checker:
        checker(
            parameter_path.exists(),
            f"Parameter file {parameter_path} does not exist",
        )

        try:
            data = json.loads(parameter_path.read_text())
            is_valid_json = True
        except Exception:
            is_valid_json = False
        checker(is_valid_json, f"The parameter file at {parameter_path} is not valid JSON")

    # Make static type checkers happy
    assert data is not None
    return data


def fetch_job_script_data(
    jg_ctx: JobbergateContext,
    id: int,
) -> JobScriptResponse:
    """
    Retrieve a job_script from the API by ``id``
    """
    # Make static type checkers happy
    assert jg_ctx.client is not None

    return cast(
        JobScriptResponse,
        make_request(
            jg_ctx.client,
            f"/jobbergate/job-scripts/{id}",
            "GET",
            expected_status=200,
            abort_message=f"Couldn't retrieve job script ({id}) from API",
            support=True,
            response_model_cls=JobScriptResponse,
        ),
    )
