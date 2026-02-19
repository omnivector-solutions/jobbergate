"""Unit tests for retry utility functions."""

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from jobbergate_api.retry_utils import async_retry, sync_retry


class TestAsyncRetry:
    """Tests for async_retry function."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Test successful function execution on first attempt."""
        mock_func = AsyncMock(return_value="success")
        mock_func.__name__ = "test_func"
        result = await async_retry(mock_func)
        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_success_on_second_attempt(self):
        """Test successful function execution after one failure."""
        mock_func = AsyncMock(side_effect=[Exception("fail"), "success"])
        mock_func.__name__ = "test_func"
        result = await async_retry(mock_func, max_attempts=3)
        assert result == "success"
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_success_on_third_attempt(self):
        """Test successful function execution after two failures."""
        mock_func = AsyncMock(
            side_effect=[
                Exception("fail1"),
                Exception("fail2"),
                "success",
            ]
        )
        mock_func.__name__ = "test_func"
        result = await async_retry(mock_func, max_attempts=3)
        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_failure_after_max_attempts(self):
        """Test returnNone when all retries are exhausted."""
        mock_func = AsyncMock(side_effect=Exception("persistent failure"))
        mock_func.__name__ = "test_func"
        result = await async_retry(mock_func, max_attempts=3)
        assert result is None
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test that exponential backoff delays increase correctly."""
        mock_func = AsyncMock(side_effect=Exception("fail"))
        mock_func.__name__ = "test_func"

        with patch("jobbergate_api.retry_utils.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await async_retry(
                mock_func,
                max_attempts=4,
                initial_delay=1.0,
                backoff_factor=2.0,
            )

            # Should be called with 1.0, 2.0, 4.0 (three delays for 4 attempts)
            assert mock_sleep.call_count == 3
            calls = [call(delay) for delay in [1.0, 2.0, 4.0]]
            mock_sleep.assert_has_calls(calls)

    @pytest.mark.asyncio
    async def test_on_error_callback_invoked(self):
        """Test that on_error callback is invoked on each failure."""
        mock_func = AsyncMock(side_effect=Exception("fail"))
        mock_func.__name__ = "test_func"
        on_error_callback = MagicMock()

        await async_retry(
            mock_func,
            max_attempts=3,
            on_error=on_error_callback,
        )

        assert on_error_callback.call_count == 3
        # Verify attempt numbers are passed correctly (1, 2, 3)
        for call_args, expected_attempt in zip(on_error_callback.call_args_list, [1, 2, 3]):
            args, _ = call_args
            exc, attempt = args
            assert isinstance(exc, Exception)
            assert exc.args[0] == "fail"
            assert attempt == expected_attempt

    @pytest.mark.asyncio
    async def test_with_function_args_and_kwargs(self):
        """Test that args and kwargs are passed to the function."""
        mock_func = AsyncMock(return_value="result")
        mock_func.__name__ = "test_func"
        result = await async_retry(
            mock_func,
            "arg1",
            "arg2",
            kwarg1="value1",
            kwarg2="value2",
        )
        assert result == "result"
        mock_func.assert_called_once_with("arg1", "arg2", kwarg1="value1", kwarg2="value2")

    @pytest.mark.asyncio
    async def test_error_logging_on_exhaustion(self):
        """Test that error is logged when all retries are exhausted."""
        test_exception = Exception("test failure")
        mock_func = AsyncMock(side_effect=test_exception)
        mock_func.__name__ = "test_func"

        with patch("jobbergate_api.retry_utils.logger") as mock_logger:
            result = await async_retry(mock_func, max_attempts=2)
            assert result is None
            # Verify error was logged with exception details
            mock_logger.error.assert_called_once()
            error_message = mock_logger.error.call_args[0][0]
            assert "test failure" in error_message
            assert "2" in error_message  # max_attempts

    @pytest.mark.asyncio
    async def test_warning_logging_without_callback(self):
        """Test that warning is logged on each failure without callback."""
        mock_func = AsyncMock(side_effect=Exception("fail"))
        mock_func.__name__ = "test_func"

        with patch("jobbergate_api.retry_utils.logger") as mock_logger:
            await async_retry(mock_func, max_attempts=2)
            # Should log warning for each failure
            assert mock_logger.warning.call_count == 2

    @pytest.mark.asyncio
    async def test_no_warning_logging_with_callback(self):
        """Test that no warning is logged when callback is provided."""
        mock_func = AsyncMock(side_effect=Exception("fail"))
        mock_func.__name__ = "test_func"
        on_error_callback = MagicMock()

        with patch("jobbergate_api.retry_utils.logger") as mock_logger:
            await async_retry(
                mock_func,
                max_attempts=2,
                on_error=on_error_callback,
            )
            # Should not log warning when callback is provided
            mock_logger.warning.assert_not_called()


class TestSyncRetry:
    """Tests for sync_retry function."""

    def test_success_on_first_attempt(self):
        """Test successful function execution on first attempt."""
        mock_func = MagicMock(return_value="success")
        mock_func.__name__ = "test_func"
        result = sync_retry(mock_func)
        assert result == "success"
        assert mock_func.call_count == 1

    def test_success_on_second_attempt(self):
        """Test successful function execution after one failure."""
        mock_func = MagicMock(side_effect=[Exception("fail"), "success"])
        mock_func.__name__ = "test_func"
        result = sync_retry(mock_func, max_attempts=3)
        assert result == "success"
        assert mock_func.call_count == 2

    def test_success_on_third_attempt(self):
        """Test successful function execution after two failures."""
        mock_func = MagicMock(
            side_effect=[
                Exception("fail1"),
                Exception("fail2"),
                "success",
            ]
        )
        mock_func.__name__ = "test_func"
        result = sync_retry(mock_func, max_attempts=3)
        assert result == "success"
        assert mock_func.call_count == 3

    def test_failure_after_max_attempts(self):
        """Test return None when all retries are exhausted."""
        mock_func = MagicMock(side_effect=Exception("persistent failure"))
        mock_func.__name__ = "test_func"

        with patch("time.sleep"):
            result = sync_retry(mock_func, max_attempts=3)

        assert result is None
        assert mock_func.call_count == 3

    def test_exponential_backoff_timing(self):
        """Test that exponential backoff delays increase correctly."""
        mock_func = MagicMock(side_effect=Exception("fail"))
        mock_func.__name__ = "test_func"

        with patch("time.sleep") as mock_sleep:
            sync_retry(
                mock_func,
                max_attempts=4,
                initial_delay=1.0,
                backoff_factor=2.0,
            )

            # Should be called with 1.0, 2.0, 4.0 (three delays for 4 attempts)
            assert mock_sleep.call_count == 3
            calls = [call(delay) for delay in [1.0, 2.0, 4.0]]
            mock_sleep.assert_has_calls(calls)

    def test_on_error_callback_invoked(self):
        """Test that on_error callback is invoked on each failure."""
        mock_func = MagicMock(side_effect=Exception("fail"))
        mock_func.__name__ = "test_func"
        on_error_callback = MagicMock()

        with patch("time.sleep"):
            sync_retry(
                mock_func,
                max_attempts=3,
                on_error=on_error_callback,
            )

        assert on_error_callback.call_count == 3
        # Verify attempt numbers are passed correctly (1, 2, 3)
        for call_args, expected_attempt in zip(on_error_callback.call_args_list, [1, 2, 3]):
            args, _ = call_args
            exc, attempt = args
            assert isinstance(exc, Exception)
            assert exc.args[0] == "fail"
            assert attempt == expected_attempt

    def test_with_function_args_and_kwargs(self):
        """Test that args and kwargs are passed to the function."""
        mock_func = MagicMock(return_value="result")
        mock_func.__name__ = "test_func"
        result = sync_retry(
            mock_func,
            "arg1",
            "arg2",
            kwarg1="value1",
            kwarg2="value2",
        )
        assert result == "result"
        mock_func.assert_called_once_with("arg1", "arg2", kwarg1="value1", kwarg2="value2")

    def test_error_logging_on_exhaustion(self):
        """Test that error is logged when all retries are exhausted."""
        test_exception = Exception("test failure")
        mock_func = MagicMock(side_effect=test_exception)
        mock_func.__name__ = "test_func"

        with patch("jobbergate_api.retry_utils.logger") as mock_logger:
            with patch("time.sleep"):
                result = sync_retry(mock_func, max_attempts=2)

            assert result is None
            # Verify error was logged with exception details
            mock_logger.error.assert_called_once()
            error_message = mock_logger.error.call_args[0][0]
            assert "test failure" in error_message
            assert "2" in error_message  # max_attempts

    def test_warning_logging_without_callback(self):
        """Test that warning is logged on each failure without callback."""
        mock_func = MagicMock(side_effect=Exception("fail"))
        mock_func.__name__ = "test_func"

        with patch("jobbergate_api.retry_utils.logger") as mock_logger:
            with patch("time.sleep"):
                sync_retry(mock_func, max_attempts=2)

            # Should log warning for each failure
            assert mock_logger.warning.call_count == 2

    def test_no_warning_logging_with_callback(self):
        """Test that no warning is logged when callback is provided."""
        mock_func = MagicMock(side_effect=Exception("fail"))
        mock_func.__name__ = "test_func"
        on_error_callback = MagicMock()

        with patch("jobbergate_api.retry_utils.logger") as mock_logger:
            with patch("time.sleep"):
                sync_retry(
                    mock_func,
                    max_attempts=2,
                    on_error=on_error_callback,
                )

            # Should not log warning when callback is provided
            mock_logger.warning.assert_not_called()
