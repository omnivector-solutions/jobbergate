"""
Provide utilities for making requests against the Jobbergate API.
"""
from typing import Any, Dict, Optional, Type, TypeVar, Union

import httpx
import pydantic
from loguru import logger

from jobbergate_cli.exceptions import Abort
from jobbergate_cli.schemas import ForeignKeyError
from jobbergate_cli.text_tools import dedent, unwrap


def _deserialize_request_model(
    request_model: pydantic.BaseModel,
    request_kwargs: Dict[str, Any],
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
        request_kwargs["content"] = request_model.json()
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
    expected_status: Optional[int] = None,
    expect_response: bool = True,
    abort_message: str = "There was an error communicating with the API",
    abort_subject: str = "REQUEST FAILED",
    support: bool = True,
    response_model_cls: Optional[Type[ResponseModel]] = None,
    request_model: Optional[pydantic.BaseModel] = None,
    **request_kwargs: Any,
) -> Union[ResponseModel, Dict, int]:
    """
    Make a request against the Jobbergate API.

    :param: client:              The Httpx client to use for the request
    :param: url_path:            The path to add to the base url of the client where the request should be sent
    :param: method:              The REST method to use for the request (GET, PUT, UPDATE, POST, DELETE, etc)
    :param: expected_status:     The status code to expect on the response. If it is not received, raise an Abort
    :param: expect_response:     Indicates if response data (JSON) is expected from the API endpoint
    :param: abort_message:       The message to show the user if there is a problem and the app must be aborted
    :param: abort_subject:       The subject to use in Abort output to the user
    :param: support:             If true, add a message to the output instructing the user to seek help
    :param: response_model_cls:  If supplied, serialize the response data into this Pydantic model class
    :param: request_model:       Use a pydantic model instance as the data body for the request
    :param: request_kwargs:      Any additional keyword arguments that need to be passed on to the client
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
        raise Abort(
            unwrap(
                f"""
                {abort_message}:
                Communication with the API failed.
                """
            ),
            subject=abort_subject,
            support=support,
            log_message="There was an error making the request to the API",
            original_error=err,
        )

    if expected_status is not None and response.status_code != expected_status:
        if method == "DELETE" and response.status_code == 409:
            details = response.json()["detail"]
            fk_error = ForeignKeyError(**details)
            raise Abort(
                dedent(
                    f"""
                    {abort_message}:
                    There are [red]{fk_error.table}[/red] that reference id [bold yellow]{fk_error.pk_id}[/bold yellow].
                    """,
                ),
                subject=abort_subject,
                log_message=f"Could not delete due to foreign-key constraint: {response.text}",
            )
        else:
            raise Abort(
                unwrap(
                    f"""
                    {abort_message}:
                    Received an error response.
                    """
                ),
                subject=abort_subject,
                support=support,
                log_message=f"Got an error code for request: {response.status_code}: {response.text}",
            )

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

    logger.debug("Validating response data with ResponseModel")
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
