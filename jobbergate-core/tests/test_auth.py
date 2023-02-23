"""
Test the utilities for handling auth in Jobbergate.
"""
from unittest.mock import patch

import pendulum
import pytest
from jose.jwt import encode

from jobbergate_core.auth import Token


@pytest.fixture(scope="session")
def time_now():
    """
    Return a pendulum instance with a fixed time.
    """
    time_now = pendulum.datetime(2020, 1, 1, tz="UTC")
    pendulum.set_test_now(time_now)

    yield time_now

    pendulum.set_test_now(None)


@pytest.fixture
def jwt_token(time_now):
    """
    This fixture will create a JWT token using the jose package.
    """

    def helper(expiration_time=time_now, **kwargs):

        payload = {
            "exp": expiration_time.int_timestamp,
            **kwargs,
        }
        jwt_token = encode(payload, "fake-secret", algorithm="HS256")

        return jwt_token

    return helper


@pytest.fixture(scope="session")
def test_token(jwt_token, tmp_path):
    """
    This fixture will create a Token instance.
    """
    token_path = tmp_path / "test.txt"
    token_content = jwt_token()

    yield Token(content=token_content, cache_path=token_path)


class TestToken:
    def test_base_case(self):
        """
        Test that the Token class can be instantiated.
        """
        token = Token()
        assert token.content is None
        assert token.cache_path is None
        assert token.label == "unknown"
        assert token.data == {}

    def test_validate_cache_path__success(self, tmp_path):
        """
        Test that the validate cache path function works as expected.
        """
        token = Token(cache_path=tmp_path / "test.txt")
        token._validate_cache_path()

    def test_validate_cache_path__path_is_none(self):
        """
        Test that validate cache path raises an exception when the path is None.
        """
        token = Token()
        with pytest.raises(Exception):
            token._validate_cache_path()

    def test_validate_cache_path__path_does_no_exist(self, tmp_path):
        """
        Test that validate cache path raises an exception when the path does not exist.
        """
        token = Token(cache_path=tmp_path / "dummy-directory" / "test.txt")
        with pytest.raises(Exception):
            token._validate_cache_path()

    def test_save_to_cache__success(self, tmp_path, jwt_token):
        """
        Test that the save_to_cache function works as expected.
        """

        token_path = tmp_path / "test.txt"
        token_content = jwt_token()

        token = Token(content=token_content, cache_path=token_path)

        with patch.object(token, "_validate_cache_path") as mocked:
            token.save_to_cache()
            mocked.assert_called_once()

        assert token_path.read_text() == token_content

    def test_save_to_cache__validation_error(self, tmp_path, jwt_token):
        """
        Test that save_to_cache raises an exception when the path is invalid.
        """
        token_path = tmp_path / "test.txt"
        token_content = jwt_token()

        token = Token(content=token_content, cache_path=token_path)

        with patch.object(token, "_validate_cache_path") as mocked:
            mocked.side_effect = Exception("Dummy error")
            with pytest.raises(Exception):
                token.save_to_cache()
            mocked.assert_called_once()

    def test_load_from_cache__success(self, tmp_path, jwt_token):
        """
        Test that the load_from_cache function works as expected.
        """

        token_path = tmp_path / "test.txt"
        token_content = jwt_token()
        token_path.write_text(token_content)

        token = Token(cache_path=token_path)

        with patch.object(token, "_validate_cache_path") as mocked:
            token.load_from_cache()
            mocked.assert_called_once()

        assert token.content == token_content

    def test_load_from_cache__validation_error(self, tmp_path, jwt_token):
        """
        Test that the load_from_cache function works as expected.
        """

        token_path = tmp_path / "test.txt"
        token = Token(cache_path=token_path)

        with patch.object(token, "_validate_cache_path") as mocked:
            mocked.side_effect = Exception("Dummy error")
            with pytest.raises(Exception):
                token.load_from_cache()
            mocked.assert_called_once()

    def test_clear_cache__success(self, tmp_path, jwt_token):
        """
        Test that the clear_cache function works as expected.
        """

        token_path = tmp_path / "test.txt"
        token_content = jwt_token()
        token_path.write_text(token_content)

        token = Token(cache_path=token_path)

        assert token_path.is_file() is True
        token.clear_cache()
        assert token_path.is_file() is False

    def test_clear_cache__file_not_found(self, tmp_path):
        """
        Test that the clear_cache raises no error if the file does no exist.
        """

        token_path = tmp_path / "test.txt"
        token = Token(cache_path=token_path)

        assert token_path.is_file() is False
        token.clear_cache()

    def test_validate_content__success(self, jwt_token):
        """
        Test that the validate_content function works as expected.
        """
        token = Token(content=jwt_token())

        token._validate_content()

    @pytest.mark.parametrize("content", [None, ""])
    def test_validate_content__invalid_token(self, content):
        """
        Test that the validate_content function raises an exception when the token is invalid.
        """
        token = Token(content=content)

        with pytest.raises(Exception):
            token._validate_content()

    def test_update_data__success(self, jwt_token, time_now):
        """
        Test that the update_data function works as expected.
        """
        token_data = {
            "test": "test",
            "foo": "bar",
            "email": "good@email.com",
            "name": "John Doe",
            "exp": time_now.int_timestamp,
        }
        token = Token(content=jwt_token(**token_data))

        with patch.object(token, "_validate_content") as mocked:
            token._update_data()
            mocked.assert_called_once()
        assert token.data == token_data

    @pytest.mark.parametrize(
        "time_delta, is_expired",
        [(-1, False), (0, True), (1, True)],
    )
    def test_is_expired__success(self, time_delta, is_expired, jwt_token, time_now):
        """
        Test that the is_expired function works as expected.
        """

        expiration_date = time_now.int_timestamp + time_delta
        token = Token(content=jwt_token(exp=expiration_date))

        assert token.is_expired() == is_expired
