"""
Test the utilities for handling auth in Jobbergate.
"""
import pytest

from jobbergate_core.auth.token import Token, TokenError, TokenType


class TestToken:
    def test_base_case(self, jwt_token, tmp_path, time_now):
        """
        Test that the Token class can be instantiated.
        """

        token_data = {
            "test": "test",
            "foo": "bar",
            "email": "good@email.com",
            "name": "John Doe",
            "exp": time_now.int_timestamp,
        }
        token_content = jwt_token(**token_data)

        token = Token(
            content=token_content,
            cache_directory=tmp_path,
            label=TokenType.ACCESS,
        )

        assert token.content == token_content
        assert token.cache_directory == tmp_path
        assert token.label == "access"
        assert token.file_path == tmp_path / "access.token"
        assert token.data == token_data

    def test_save_to_cache__success(self, tmp_path, jwt_token):
        """
        Test that the save_to_cache function works as expected.
        """

        token_content = jwt_token()

        token = Token(
            content=token_content,
            cache_directory=tmp_path,
            label=TokenType.ACCESS,
        )

        assert token.file_path.exists() is False

        token.save_to_cache()

        assert token.file_path.read_text() == token_content

    def test_save_to_cache__validation_error(self, tmp_path, jwt_token):
        """
        Test that save_to_cache raises an exception when the path is invalid.
        """
        token_directory = tmp_path / "unexistent_directory"
        token_content = jwt_token()

        token = Token(
            content=token_content,
            cache_directory=token_directory,
            label=TokenType.ACCESS,
        )

        with pytest.raises(TokenError, match="Parent directory does not exist"):
            token.save_to_cache()

    def test_load_from_cache__success(self, tmp_path, jwt_token, time_now):
        """
        Test that the load_from_cache function works as expected.
        """

        token_data = {
            "test": "test",
            "foo": "bar",
            "email": "good@email.com",
            "name": "John Doe",
            "exp": time_now.int_timestamp,
        }
        token_label = TokenType.ACCESS
        token_path = tmp_path / "access.token"
        token_content = jwt_token(**token_data)
        token_path.write_text(token_content)

        token = Token.load_from_cache(cache_directory=tmp_path, label=token_label)

        assert token.content == token_content
        assert token.cache_directory == tmp_path
        assert token.label == token_label
        assert token.file_path == token_path
        assert token.data == token_data

    def test_load_from_cache__validation_error(self, tmp_path):
        """
        Test that the load_from_cache function raises an error when the file is not found.
        """

        token_path = tmp_path / "access.token"

        assert token_path.exists() is False

        with pytest.raises(TokenError, match="Token file was not found"):
            Token.load_from_cache(cache_directory=tmp_path, label=TokenType.ACCESS)

    def test_clear_cache__success(self, tmp_path, jwt_token):
        """
        Test that the clear_cache function works as expected.
        """

        token_path = tmp_path / "access.token"
        token_content = jwt_token()
        token_path.write_text(token_content)

        token = Token(
            content=token_content,
            cache_directory=tmp_path,
            label=TokenType.ACCESS,
        )

        assert token_path.is_file() is True
        token.clear_cache()
        assert token_path.is_file() is False

    def test_clear_cache__file_not_found(self, tmp_path, jwt_token):
        """
        Test that the clear_cache raises no error if the file does no exist.
        """

        token_path = tmp_path / "access.token"
        token_content = jwt_token()

        token = Token(
            content=token_content,
            cache_directory=tmp_path,
            label=TokenType.ACCESS,
        )

        assert token_path.is_file() is False
        token.clear_cache()
        assert token_path.is_file() is False

    @pytest.mark.parametrize("test_content", ["some-dummy-text", "", None])
    def test_validate_content__invalid_token(self, test_content, tmp_path):
        """
        Test that an error is raised when the token content is invalid.
        """
        with pytest.raises(TokenError):
            Token(
                content=test_content,
                cache_directory=tmp_path,
                label=TokenType.ACCESS,
            )

    @pytest.mark.parametrize(
        "time_delta, is_expired",
        [(-1, False), (0, True), (1, True)],
    )
    def test_is_expired__success(self, time_delta, is_expired, tmp_path, jwt_token, time_now):
        """
        Test that the is_expired function works as expected.
        """
        expiration_date = time_now.int_timestamp + time_delta

        token = Token(
            content=jwt_token(exp=expiration_date),
            cache_directory=tmp_path,
            label=TokenType.ACCESS,
        )

        assert token.is_expired() == is_expired
