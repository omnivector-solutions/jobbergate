"""
Provide utilities for making requests against the Jobbergate API.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Type, TypeVar

import httpx
import pydantic
from loguru import logger

from jobbergate_cli.exceptions import Abort
from jobbergate_cli.text_tools import dedent, unwrap


def get_possible_solution_to_error(response: httpx.Response) -> str:
    """
    Get a possible solution to an error code.
    """
    if response.is_client_error:
        default_solution = "Please check the data on your request and try again"
    else:
        default_solution = "Please try again and contact support if the problem persists"

    custom_solutions: dict[int, str] = {
        # client errors
        httpx.codes.UNAUTHORIZED: "Please login and try again",
        httpx.codes.FORBIDDEN: "Unable to modify an entry owned by someone else, please contact the resource owner"
        if "mismatch on attribute" in response.text.lower()
        else "Please verify your credentials to perform this action with a system admin",
        httpx.codes.NOT_FOUND: "Please check the id number or identifier and try again",
        httpx.codes.REQUEST_TIMEOUT: "Please try again and contact support if the problem persists",
        # server errors
        # ...
    }
    return custom_solutions.get(response.status_code, default_solution)


def format_response_error(response: httpx.Response, default_text) -> str:
    """
    Format a response into a human-readable error message, including the cause, and a possible solution.
    """
    message = [default_text]
    try:
        message.append(response.json()["detail"])
    except Exception:
        pass
    message.append(get_possible_solution_to_error(response))
    return " -- ".join(message)


def _deserialize_request_model(
    request_model: pydantic.BaseModel,
    request_kwargs: dict[str, Any],
    abort_message: str,
    abort_subject: str,
):
    """
    Deserialize a pydantic model instance into request_kwargs for an httpx client request in place.
    """
    sentry_context = dict(
        make_request=dict(
            request_model=request_model,
            request_kwargs=request_kwargs,
        ),
    )
    Abort.require_condition(
        all(
            [
                "data" not in request_kwargs,
                "json" not in request_kwargs,
                "content" not in request_kwargs,
            ]
        ),
        unwrap(
            f"""
            {abort_message}:
            Request was incorrectly structured.
            """
        ),
        raise_kwargs=dict(
            subject=abort_subject,
            support=True,
            log_message=unwrap(
                """
                When using `request_model`, you may not pass
                `data`, `json`, or `content` in the `request_kwargs`
                """
            ),
            sentry_context=sentry_context,
        ),
    )
    try:
        request_kwargs["content"] = request_model.model_dump_json()
        request_kwargs["headers"] = {"Content-Type": "application/json"}
    except Exception as err:
        raise Abort(
            unwrap(
                f"""
                {abort_message}:
                Request data could not be deserialized for http request.
                """
            ),
            subject=abort_subject,
            support=True,
            log_message=unwrap(
                f"""
                Could not deserialize instance of {request_model.__class__}:
                {request_model}
                """
            ),
            sentry_context=sentry_context,
            original_error=err,
        )


ResponseModel = TypeVar("ResponseModel", bound=pydantic.BaseModel)


def make_request(
    client: httpx.Client,
    url_path: str,
    method: str,
    *,
    expected_status: int | None = None,
    expect_response: bool = True,
    abort_message: str = "There was an error communicating with the API",
    abort_subject: str = "REQUEST FAILED",
    support: bool = True,
    response_model_cls: Type[ResponseModel] | None = None,
    request_model: pydantic.BaseModel | None = None,
    save_to_file: Path | None = None,
    **request_kwargs: Any,
) -> ResponseModel | dict | int:
    """
    Make a request against the Jobbergate API.

    Args:
        client: The Httpx client to use for the request.
        url_path: The path to add to the base url of the client where the request should be sent.
        method: The REST method to use for the request (GET, PUT, UPDATE, POST, DELETE, etc).
        expected_status: The status code to expect on the response. If it is not received, raise an Abort.
        expect_response: Indicates if response data (JSON) is expected from the API endpoint.
        abort_message: The message to show the user if there is a problem and the app must be aborted.
        abort_subject: The subject to use in Abort output to the user.
        support: If true, add a message to the output instructing the user to seek help.
        response_model_cls: If supplied, serialize the response data into this Pydantic model class.
        request_model: Use a pydantic model instance as the data body for the request.
        save_to_file: If supplied, save the response data to this file.
        request_kwargs: Any additional keyword arguments to pass to the request.

    Returns:
        The response from the API, either as a Pydantic model, a dictionary, or an integer status code.
    """

    if request_model is not None:
        _deserialize_request_model(request_model, request_kwargs, abort_message, abort_subject)

    logger.debug(f"Making request to url_path={url_path}")
    request = client.build_request(method, url_path, **request_kwargs)

    # Look for the request body in the request_kwargs
    debug_request_body = request_kwargs.get("data", request_kwargs.get("json", request_kwargs.get("content")))
    logger.debug(
        dedent(
            f"""
            Request built with:
              url:     {request.url}
              method:  {method}
              headers: {request.headers}
              body:    {debug_request_body}
            """
        )
    )

    try:
        response = client.send(request)
    except httpx.RequestError as err:
        exception_name = type(err).__name__
        raise Abort(
            unwrap(
                f"""
                {abort_message}:
                Communication with the API failed: {str(err)}.
                """
            ),
            subject=f"{abort_subject} - {exception_name}",
            support=support,
            log_message=f"There was an error on the request -- {str(err)}",
            original_error=err,
        )

    if expected_status is not None:
        if response.is_client_error:
            raise Abort(
                format_response_error(response, abort_message),
                subject=f"{abort_subject} - {response.reason_phrase}",
                log_message="Request was invalid due to a client-side error ({} -- {}): {}".format(
                    response.status_code, response.reason_phrase, response.text
                ),
                support=support if response.status_code != httpx.codes.FORBIDDEN else False,
            )
        elif response.is_server_error:
            raise Abort(
                format_response_error(response, abort_message),
                subject=f"{abort_subject} - {response.reason_phrase}",
                log_message="Request was invalid due to a server-side error ({} -- {}): {}".format(
                    response.status_code, response.reason_phrase, response.text
                ),
                support=True,
                sentry_context=dict(
                    url=request.url, method=method, request_kwargs=request_kwargs, response=response.text
                ),
            )
        elif expected_status != response.status_code:
            raise Abort(
                unwrap(
                    f"""
                        {abort_message}:
                        Received an error response.
                        """
                ),
                subject=abort_subject,
                support=support,
                log_message="Got an unexpected error code on request (expected {}, got {}): {}".format(
                    expected_status, response.status_code, response.text
                ),
            )

    if save_to_file is not None:
        save_to_file.parent.mkdir(parents=True, exist_ok=True)
        save_to_file.write_bytes(response.content)
        return response.status_code

    # TODO: constrain methods with a named enum
    if expect_response is False or method == "DELETE":
        return response.status_code

    try:
        data = response.json()
    except Exception as err:
        raise Abort(
            unwrap(
                f"""
                {abort_message}:
                Response carried no data.
                """
            ),
            subject=abort_subject,
            support=support,
            log_message=f"Failed unpacking json: {response.text}",
            original_error=err,
        )
    logger.debug(f"Extracted data from response: {data}")

    if response_model_cls is None:
        return data

    logger.debug(f"Validating response data with {response_model_cls}")
    try:
        return response_model_cls(**data)
    except pydantic.ValidationError as err:
        raise Abort(
            unwrap(
                f"""
                {abort_message}:
                Unexpected data in response.
                """
            ),
            subject=abort_subject,
            support=support,
            log_message=f"Unexpected format in response data: {data}",
            original_error=err,
        )
