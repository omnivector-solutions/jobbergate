import typing

import httpx
from loguru import logger
import pydantic
import snick

from jobbergate_cli.exceptions import Abort


ResponseModel = typing.TypeVar("ResponseModel", bound=pydantic.BaseModel)


def make_request(
    client: httpx.Client,
    url_path: str,
    method: str,
    *,
    expected_status: typing.Optional[int] = None,
    expect_response: bool = True,
    abort_message: str = "There was an error communicating with the API",
    abort_subject: str = "REQUEST FAILED",
    support: bool = True,
    response_model: typing.Optional[typing.Type[ResponseModel]] = None,
    **request_kwargs: typing.Any,
) -> typing.Union[ResponseModel, typing.Dict, int]:

    logger.debug(f"Making request to {url_path=}")
    request = client.build_request(method, url_path, **request_kwargs)
    logger.debug(f"Request built as {request=}")

    try:
        response = client.send(request)
    except httpx.RequestError as err:
        raise Abort(
            snick.unwrap(
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
        raise Abort(
            snick.unwrap(
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
    if method == "DELETE" or expect_response is False:
        return response.status_code

    try:
        data = response.json()
    except Exception as err:
        raise Abort(
            snick.unwrap(
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

    if response_model is None:
        return data

    logger.debug("Validating response data with ResponseModel")
    try:
        return response_model(**data)
    except pydantic.ValidationError as err:
        raise Abort(
            snick.unwrap(
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
