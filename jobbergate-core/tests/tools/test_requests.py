import json
from typing import Dict, Optional

import httpx
import pydantic
import pytest

from jobbergate_core.tools.requests import (
    JobbergateResponseError,
    RequestHandler,
    RequestModelError,
    deserialize_request_model,
)

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


def test__deserialize_request_model__success():
    """
    Validate that the ``_deserialize_request_model`` method can successfully deserialize a pydantic model instance into
    the ``content`` part of the ``request_kwargs``. Also, validate that the ``content-type`` part of the request is set
    to ``application/json``.
    """
    request_kwargs = dict()
    deserialize_request_model(DummyResponseModel(foo=1, bar="one"), request_kwargs)
    assert json.loads(request_kwargs["content"]) == dict(foo=1, bar="one")
    assert request_kwargs["headers"] == {"Content-Type": "application/json"}


def test__deserialize_request_model__raises_Abort_if_request_kwargs_already_has_other_body_parts():
    """
    Validate that the ``_deserialize_request_model`` raises an Abort if the ``request_kwargs`` already has a "body" part
    (``data``, ``json``, or ``content``).
    """
    with pytest.raises(RequestModelError, match="Request was incorrectly structured"):
        deserialize_request_model(DummyResponseModel(foo=1, bar="one"), dict(data=dict(foo=11)))

    with pytest.raises(RequestModelError, match="Request was incorrectly structured"):
        deserialize_request_model(DummyResponseModel(foo=1, bar="one"), dict(json=dict(foo=11)))

    with pytest.raises(RequestModelError, match="Request was incorrectly structured"):
        deserialize_request_model(DummyResponseModel(foo=1, bar="one"), dict(content=json.dumps(dict(foo=11))))


class TestRequestHandler:
    def test_make_request__success(self, respx_mock, dummy_client):
        """
        Validate that the RequestHandler can successfully make a request.
        """

        client = dummy_client(headers={"content-type": "garbage"})
        req_path = "/fake-path"

        reponse_status = httpx.codes.OK
        response_json = dict(
            foo=1,
            bar="one",
        )
        mocked_get = respx_mock.get(f"{DEFAULT_DOMAIN}{req_path}").mock(
            return_value=httpx.Response(reponse_status, json=response_json),
        )

        request_handler = RequestHandler(client=client, url_path=req_path, method="GET")

        assert mocked_get.call_count == 1

        assert request_handler.response.status_code == reponse_status
        assert request_handler.response.json() == response_json

    def test_make_request__raises_request_error(self, respx_mock, dummy_client):
        """
        Validate that the RequestHandler raises an error if the request fails.
        """

        client = dummy_client(headers={"content-type": "garbage"})
        req_path = "/fake-path"
        original_error = httpx.RequestError("BOOM!")

        mocked_get = respx_mock.get(f"{DEFAULT_DOMAIN}{req_path}").mock(side_effect=original_error)

        with pytest.raises(httpx.RequestError, match="BOOM!"):
            RequestHandler(client=client, url_path=req_path, method="GET")

        assert mocked_get.call_count == 1

    def test_raise_for_status__success(self, respx_mock, dummy_client):
        """
        Validate that the RequestHandler can successfully raise an error if the response status code is not 2XX.
        """

        client = dummy_client(headers={"content-type": "garbage"})
        req_path = "/fake-path"

        mocked_get = respx_mock.get(f"{DEFAULT_DOMAIN}{req_path}").mock(
            return_value=httpx.Response(httpx.codes.BAD_REQUEST),
        )

        request_handler = RequestHandler(client=client, url_path=req_path, method="GET")

        with pytest.raises(httpx.HTTPStatusError, match="Client error '400 Bad Request'"):
            request_handler.raise_for_status()

        assert mocked_get.call_count == 1

    def test_check_status_code__success(self, respx_mock, dummy_client):
        """
        Validate that the RequestHandler can successfully check the response status code.
        """

        client = dummy_client(headers={"content-type": "garbage"})
        req_path = "/fake-path"

        mocked_get = respx_mock.get(f"{DEFAULT_DOMAIN}{req_path}").mock(
            return_value=httpx.Response(httpx.codes.OK),
        )

        request_handler = RequestHandler(client=client, url_path=req_path, method="GET")

        assert request_handler.check_status_code(httpx.codes.OK)

        assert mocked_get.call_count == 1

    def test_check_status_code__raises_error(self, respx_mock, dummy_client):
        """
        Validate that the RequestHandler raises an error if the response status code is not in the provided list.
        """

        client = dummy_client(headers={"content-type": "garbage"})
        req_path = "/fake-path"

        mocked_get = respx_mock.get(f"{DEFAULT_DOMAIN}{req_path}").mock(
            return_value=httpx.Response(httpx.codes.BAD_REQUEST),
        )

        request_handler = RequestHandler(client=client, url_path=req_path, method="GET")

        with pytest.raises(httpx.HTTPStatusError, match="Unexpected response status code"):
            request_handler.check_status_code(httpx.codes.OK)

        assert mocked_get.call_count == 1

    def test_check_status_code__raises_error__with_multiple_status_codes(self, respx_mock, dummy_client):
        """
        Validate that the RequestHandler raises an error if the response status code is not in the provided list.
        """

        client = dummy_client(headers={"content-type": "garbage"})
        req_path = "/fake-path"

        mocked_get = respx_mock.get(f"{DEFAULT_DOMAIN}{req_path}").mock(
            return_value=httpx.Response(httpx.codes.BAD_REQUEST),
        )

        request_handler = RequestHandler(client=client, url_path=req_path, method="GET")

        with pytest.raises(httpx.HTTPStatusError, match="Unexpected response status code"):
            request_handler.check_status_code(httpx.codes.OK, httpx.codes.CREATED)

        assert mocked_get.call_count == 1

    def test_to_file__success(self, respx_mock, dummy_client, tmp_path):
        """
        Assert that the RequestHandler can successfully write the response content to a file.
        """

        client = dummy_client(headers={"content-type": "garbage"})
        req_path = "/fake-path"

        response_content = "Hello, World!"
        mocked_get = respx_mock.get(f"{DEFAULT_DOMAIN}{req_path}").mock(
            return_value=httpx.Response(httpx.codes.OK, content=response_content),
        )

        request_handler = RequestHandler(client=client, url_path=req_path, method="GET")

        file_path = tmp_path / "response.txt"
        assert request_handler.to_file(file_path) == file_path

        assert file_path.read_text() == response_content

        assert mocked_get.call_count == 1

    def test_to_file__fails(self, respx_mock, dummy_client, tmp_path):
        """
        Assert that the RequestHandler raises an error if the response content is empty.
        """

        client = dummy_client(headers={"content-type": "garbage"})
        req_path = "/fake-path"

        mocked_get = respx_mock.get(f"{DEFAULT_DOMAIN}{req_path}").mock(
            return_value=httpx.Response(httpx.codes.OK),
        )

        request_handler = RequestHandler(client=client, url_path=req_path, method="GET")

        file_path = tmp_path / "unexistent-directory" / "response.txt"
        with pytest.raises(JobbergateResponseError, match="Failed writing file"):
            request_handler.to_file(file_path)

        assert mocked_get.call_count == 1

    def test_to_json__success(self, respx_mock, dummy_client):
        """
        Assert that the RequestHandler can successfully write the response content to a file.
        """

        client = dummy_client(headers={"content-type": "application/json"})
        req_path = "/fake-path"

        response_json = dict(foo=1, bar="one")
        mocked_get = respx_mock.get(f"{DEFAULT_DOMAIN}{req_path}").mock(
            return_value=httpx.Response(httpx.codes.OK, json=response_json),
        )

        request_handler = RequestHandler(client=client, url_path=req_path, method="GET")

        assert request_handler.to_json() == response_json

        assert mocked_get.call_count == 1

    def test_to_json__fails(self, respx_mock, dummy_client):
        """
        Assert that the RequestHandler raises an error if the response content is empty.
        """

        client = dummy_client(headers={"content-type": "application/json"})
        req_path = "/fake-path"

        mocked_get = respx_mock.get(f"{DEFAULT_DOMAIN}{req_path}").mock(
            return_value=httpx.Response(httpx.codes.OK),
        )

        request_handler = RequestHandler(client=client, url_path=req_path, method="GET")

        with pytest.raises(JobbergateResponseError, match="Failed unpacking json from response"):
            request_handler.to_json()

        assert mocked_get.call_count == 1

    def test_to_model__success(self, respx_mock, dummy_client):
        """
        Assert that the RequestHandler can successfully write the response content to a file.
        """

        client = dummy_client(headers={"content-type": "application/json"})
        req_path = "/fake-path"

        response_json = dict(foo=1, bar="one")
        mocked_get = respx_mock.get(f"{DEFAULT_DOMAIN}{req_path}").mock(
            return_value=httpx.Response(httpx.codes.OK, json=response_json),
        )

        request_handler = RequestHandler(client=client, url_path=req_path, method="GET")

        assert request_handler.to_model(DummyResponseModel) == DummyResponseModel.model_validate(response_json)

        assert mocked_get.call_count == 1

    def test_to_model__fails(self, respx_mock, dummy_client):
        """
        Assert that the RequestHandler raises an error if the response content is empty.
        """

        client = dummy_client(headers={"content-type": "application/json"})
        req_path = "/fake-path"

        mocked_get = respx_mock.get(f"{DEFAULT_DOMAIN}{req_path}").mock(
            return_value=httpx.Response(httpx.codes.OK),
        )

        request_handler = RequestHandler(client=client, url_path=req_path, method="GET")

        with pytest.raises(JobbergateResponseError, match="Failed to validate response to model"):
            request_handler.to_model(DummyResponseModel)

        assert mocked_get.call_count == 1
