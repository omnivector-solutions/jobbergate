from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent
from typing import Any, Type, TypeVar

from buzz import check_expressions, handle_errors
from httpx import Client, HTTPStatusError, RequestError, Response, Request
from loguru import logger
from pydantic import BaseModel


class JobbergateRequestError(RequestError):
    """
    Jobbergate specific exceptions that may occur when preparing a request.
    """


class RequestModelError(JobbergateRequestError):
    """
    An error occurred while preparing the request data from a model.
    """


class JobbergateResponseError(HTTPStatusError):
    """
    Jobbergate specific exceptions that may occur when handling a response.
    """


ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


def deserialize_request_model(request_model: BaseModel, request_kwargs: dict[str, Any]) -> None:
    """
    Deserialize a pydantic model instance into request_kwargs for an httpx client request in place.
    """
    with check_expressions(
        "Request was incorrectly structured to use a `request_model`",
        raise_exc_class=RequestModelError,
    ) as check:
        for key in ("data", "json", "content"):
            check(key not in request_kwargs, f"It already contains '{key}'")

    with handle_errors("Failed to deserialize request model", raise_exc_class=RequestModelError):
        request_kwargs["content"] = request_model.model_dump_json()

    request_kwargs["headers"] = {"Content-Type": "application/json"}


@dataclass
class RequestHandler:
    """
    Provide utilities for making requests and handling responses.

    Notice most methods return self as a syntax sugar to allow chaining.

    Arguments:
      client: The httpx client to use for the request
      url_path: The path to add to the base url of the client where the request should be sent
      method: The REST method to use for the request (GET, PUT, UPDATE, POST, DELETE, etc)
      request_model: Use a pydantic model instance as the data body for the request
      request_kwargs: Any additional keyword arguments that need to be passed on to the client

    Attributes:
      response: The response object from the request is kept for reference.
    """

    client: Client
    url_path: str
    method: str  # HTTPMethod is new in Python 3.11 and can replace string here
    request_model: BaseModel | None = None
    request_kwargs: dict[str, Any] = field(default_factory=dict)
    sensitive_keys: set[str] = field(default_factory=set)

    request: Request = field(init=False, repr=False)
    response: Response = field(init=False, repr=False)

    def __post_init__(self):
        """
        Post init method.
        """
        logger.debug(f"Making request to url_path={self.url_path}")

        if self.request_model is not None:
            try:
                deserialize_request_model(self.request_model, self.request_kwargs)
            except RequestModelError as err:
                logger.error(str(err))
                raise err

        self.request = self.client.build_request(self.method, self.url_path, **self.request_kwargs)

        # Look for the request body in the request_kwargs
        debug_request_body = self.request_kwargs.get(
            "data", self.request_kwargs.get("json", self.request_kwargs.get("content"))
        )
        logger.debug(
            dedent(
                """
                Request built with:
                url:     {}
                method:  {}
                headers: {}
                body:    {}
                """
            ).strip(),
            self.request.url,
            self.method,
            self._sanitize_data(dict(self.request.headers)),
            self._sanitize_data(debug_request_body),
        )

        try:
            self.response = self.client.send(self.request)
        except RequestError as err:
            logger.error(str(err))
            raise err

        logger.debug(f"Response received with status: {self.response.reason_phrase} [{self.response.status_code}]")

    def raise_for_status(self) -> RequestHandler:
        """
        Raise the `HTTPStatusError` if one occurred.
        """
        try:
            self.response.raise_for_status()
        except HTTPStatusError as err:
            original_error_message = str(err)
            logger.error(original_error_message)
            raise JobbergateResponseError(
                message=original_error_message, request=self.request, response=self.response
            ) from err
        return self

    def check_status_code(self, *statuses: int) -> RequestHandler:
        """
        Check if the response status code is in the provided set of status codes.
        """
        if self.response.status_code not in set(statuses):
            message = "Unexpected response status code. Got: {}. Expected one of: {}".format(
                self.response.status_code, ", ".join(str(status) for status in statuses)
            )
            logger.error(message)
            raise JobbergateResponseError(message=message, request=self.request, response=self.response)
        return self

    def to_file(self, file_path: Path) -> Path:
        """
        Write the response content to a file.
        """
        try:
            file_path.write_bytes(self.response.content)
        except Exception as err:
            logger.error(str(err))
            raise JobbergateResponseError(
                message=f"Failed writing file to {file_path.as_posix()}", request=self.request, response=self.response
            ) from err
        return file_path

    def to_json(self) -> dict[str, Any]:
        """
        Unpack the response content as json.
        """
        try:
            data = self.response.json()
        except Exception as err:
            logger.error(str(err))
            raise JobbergateResponseError(
                message="Failed unpacking json from response", request=self.request, response=self.response
            ) from err

        logger.debug("Extracted data from response: {}", self._sanitize_data(data))
        return data

    def to_model(self, model: Type[ResponseModel]) -> ResponseModel:
        """
        Unpack the response content as json and validate it against a pydantic model.
        """
        try:
            return model.model_validate(self.to_json())
        except Exception as err:
            logger.error(str(err))
            raise JobbergateResponseError(
                message="Failed to validate response to model", request=self.request, response=self.response
            ) from err

    def _sanitize_data(self, data: Any) -> Any:
        """
        Sanitize sensitive data in the request body and headers.
        """
        if self.sensitive_keys and isinstance(data, dict):
            return {
                key: "*****" if key.lower() in self.sensitive_keys else self._sanitize_data(value)
                for key, value in data.items()
            }
        return data
