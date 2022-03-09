import json
from typing import Dict, Optional

import httpx
import pydantic
import pytest

from jobbergate_cli.exceptions import Abort
from jobbergate_cli.requests import make_request


DEFAULT_DOMAIN = "https://dummy-domain.com"


@pytest.fixture
def dummy_client():
    """
    Provide factory for a test client. Can supply custom base_url and headers.
    """

    def _helper(base_url: str = DEFAULT_DOMAIN, headers: Optional[Dict] = None) -> httpx.Client:
        """
        Create the dummy httpx client.
        """
        if headers is None:
            headers = dict()

        return httpx.Client(base_url=base_url, headers=headers)

    return _helper


class DummyResponseModel(pydantic.BaseModel):
    """
    Provide a dummy pydantic model for testing standard responses.
    """

    foo: int
    bar: str


class ErrorResponseModel(pydantic.BaseModel):
    """
    Provide a dummy pydantic model for testing error responses.
    """

    error: str


def test_make_request__success(respx_mock, dummy_client):
    """
    Validate that the ``make_request()`` function will make a request to the supplied path for the
    client domain, check the status code, extract the data, validate it, and return an instance of the
    supplied response model.
    """

    client = dummy_client(headers={"content-type": "garbage"})
    req_path = "/fake-path"

    respx_mock.get(f"{DEFAULT_DOMAIN}{req_path}").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dict(
                foo=1,
                bar="one",
            ),
        ),
    )
    dummy_response_instance = make_request(
        client,
        req_path,
        "GET",
        expected_status=200,
        response_model=DummyResponseModel,
    )
    assert isinstance(dummy_response_instance, DummyResponseModel)
    assert dummy_response_instance.foo == 1
    assert dummy_response_instance.bar == "one"


def test_make_request__raises_Abort_if_client_request_raises_exception(respx_mock, dummy_client):
    """
    Validate that the ``make_request()`` function will raise an Abort if the call to ``client.send`` raises an
    exception.
    """
    client = dummy_client(headers={"content-type": "garbage"})
    req_path = "/fake-path"
    original_error = httpx.RequestError("BOOM!")

    respx_mock.get(f"{DEFAULT_DOMAIN}{req_path}").mock(side_effect=original_error)

    with pytest.raises(Abort, match="There was a big problem: Communication with the API failed") as err_info:
        make_request(
            client, req_path, "GET", abort_message="There was a big problem", abort_subject="BIG PROBLEM", support=True
        )
    assert err_info.value.subject == "BIG PROBLEM"
    assert err_info.value.support is True
    assert err_info.value.log_message == "There was an error making the request to the API"
    assert err_info.value.original_error == original_error


def test_make_request__raises_Abort_when_expected_status_is_not_None_and_response_status_does_not_match_it(
    respx_mock, dummy_client
):
    """
    Validate that the ``make_request()`` function will raise an Abort if the ``expected_status`` arg is set and it
    does not match the status code of the response.
    """
    client = dummy_client(headers={"content-type": "garbage"})
    req_path = "/fake-path"

    respx_mock.get(f"{DEFAULT_DOMAIN}{req_path}").mock(
        return_value=httpx.Response(
            httpx.codes.BAD_REQUEST,
            text="It blowed up",
        ),
    )

    with pytest.raises(Abort, match="There was a big problem: Received an error response") as err_info:
        make_request(
            client,
            req_path,
            "GET",
            expected_status=200,
            abort_message="There was a big problem",
            abort_subject="BIG PROBLEM",
            support=True,
        )
    assert err_info.value.subject == "BIG PROBLEM"
    assert err_info.value.support is True
    assert err_info.value.log_message == "Got an error code for request: 400: It blowed up"
    assert err_info.value.original_error is None


def test_make_request__does_not_raise_Abort_when_expected_status_is_None_and_response_status_is_a_fail_code(
    respx_mock, dummy_client
):
    """
    Validate that the ``make_request()`` function will not raise an Abort if the ``expected_status`` arg is not set
    and the response is an error status code.
    """
    client = dummy_client(headers={"content-type": "garbage"})
    req_path = "/fake-path"

    respx_mock.get(f"{DEFAULT_DOMAIN}{req_path}").mock(
        return_value=httpx.Response(
            httpx.codes.BAD_REQUEST,
            json=dict(error="It blowed up"),
        ),
    )

    err = make_request(
        client,
        req_path,
        "GET",
        response_model=ErrorResponseModel,
    )
    assert err.error == "It blowed up"


def test_make_request__returns_the_response_status_code_if_the_method_is_DELETE(respx_mock, dummy_client):
    """
    Validate that the ``make_request()`` function will return None if the ``method`` arg is DELETE and the request
    was successfull.
    """
    client = dummy_client(headers={"content-type": "garbage"})
    req_path = "/fake-path"

    respx_mock.delete(f"{DEFAULT_DOMAIN}{req_path}").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dict(error="It blowed up"),
        ),
    )

    assert make_request(client, req_path, "DELETE") == httpx.codes.OK


def test_make_request__returns_the_response_status_code_if_expect_response_is_False(respx_mock, dummy_client):
    """
    Validate that the ``make_request()`` function will return None if the ``expect_response`` arg is False and the
    request was successfull.
    """
    client = dummy_client(headers={"content-type": "garbage"})
    req_path = "/fake-path"

    respx_mock.post(f"{DEFAULT_DOMAIN}{req_path}").mock(
        return_value=httpx.Response(httpx.codes.BAD_REQUEST),
    )

    assert make_request(client, req_path, "POST", expect_response=False) == httpx.codes.BAD_REQUEST


def test_make_request__raises_an_Abort_if_the_response_cannot_be_deserialized_with_JSON(respx_mock, dummy_client):
    """
    Validate that the ``make_request()`` function will raise an Abort if the response is not JSON de-serializable.
    """
    client = dummy_client(headers={"content-type": "garbage"})
    req_path = "/fake-path"

    respx_mock.get(f"{DEFAULT_DOMAIN}{req_path}").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            text="Not JSON, my dude",
        ),
    )

    with pytest.raises(Abort, match="There was a big problem: Response carried no data") as err_info:
        make_request(
            client, req_path, "GET", abort_message="There was a big problem", abort_subject="BIG PROBLEM", support=True
        )
    assert err_info.value.subject == "BIG PROBLEM"
    assert err_info.value.support is True
    assert err_info.value.log_message == "Failed unpacking json: Not JSON, my dude"
    assert isinstance(err_info.value.original_error, json.decoder.JSONDecodeError)


def test_make_request__returns_a_plain_dict_if_response_model_is_None(respx_mock, dummy_client):
    """
    Validate that the ``make_request()`` function will return a plain dictionary containing the response data if the
    ``response_model`` argument is not supplied.
    """
    client = dummy_client(headers={"content-type": "garbage"})
    req_path = "/fake-path"

    respx_mock.get(f"{DEFAULT_DOMAIN}{req_path}").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dict(a=1, b=2, c=3),
        ),
    )

    assert make_request(client, req_path, "GET") == dict(a=1, b=2, c=3)


def test_make_request__raises_an_Abort_if_the_response_data_cannot_be_serialized_into_the_response_model(
    respx_mock, dummy_client
):
    """
    Validate that the ``make_request()`` function will raise an Abort if the response data cannot be serialized as and
    validated with the ``response_model``.
    """
    client = dummy_client(headers={"content-type": "garbage"})
    req_path = "/fake-path"

    respx_mock.get(f"{DEFAULT_DOMAIN}{req_path}").mock(
        return_value=httpx.Response(
            httpx.codes.OK,
            json=dict(a=1, b=2, c=3),
        ),
    )

    with pytest.raises(Abort, match="There was a big problem: Unexpected data in response") as err_info:
        make_request(
            client,
            req_path,
            "GET",
            abort_message="There was a big problem",
            abort_subject="BIG PROBLEM",
            support=True,
            response_model=DummyResponseModel,
        )
    assert err_info.value.subject == "BIG PROBLEM"
    assert err_info.value.support is True
    assert err_info.value.log_message == f"Unexpected format in response data: {dict(a=1, b=2, c=3)}"
    assert isinstance(err_info.value.original_error, pydantic.ValidationError)
