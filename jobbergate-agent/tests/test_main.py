from unittest import mock

from jobbergate_agent.main import main


@mock.patch("jobbergate_agent.main.asyncio")
def test_main__checks_if_agent_asyncio_loop_is_run_forever(mock_asyncio):
    """Checks whether the corountine that runs all functionality is called or not."""

    mocked_loop = mock.MagicMock()
    mock_asyncio.get_event_loop = mock.MagicMock(return_value=mocked_loop)

    main()

    mock_asyncio.get_event_loop.assert_called_once()
    mocked_loop.run_forever.assert_called_once()


@mock.patch("jobbergate_agent.main.asyncio.get_event_loop")
@mock.patch("jobbergate_agent.main.init_sentry")
@mock.patch("jobbergate_agent.main.init_scheduler")
@mock.patch("jobbergate_agent.main.logger.info")
def test_main__calls_expected_functions(*mocked):
    """Checks whether the main function calls all expected functions."""
    main()
    assert all(m.call_count == 1 for m in mocked)


@mock.patch("jobbergate_agent.main.init_sentry")
@mock.patch("jobbergate_agent.main.init_scheduler")
@mock.patch("jobbergate_agent.main.shut_down_scheduler")
@mock.patch("jobbergate_agent.main.logger.info")
def test_main__calls_expected_on_shut_down(*mocked):
    """Checks whether the main function calls all expected functions when shutting down."""
    with mock.patch("jobbergate_agent.main.asyncio.get_event_loop") as mock_loop:
        mock_loop.side_effect = KeyboardInterrupt()
        main()
    assert all(m.call_count == 1 for m in mocked)
