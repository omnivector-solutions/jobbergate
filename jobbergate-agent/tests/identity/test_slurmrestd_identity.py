from datetime import datetime, timedelta, timezone
from unittest import mock

from freezegun import freeze_time
from jose import jwt

from jobbergate_agent.identity.slurmrestd import SETTINGS, acquire_token
from jobbergate_agent.utils.logging import logger


def test_acquire_token__gets_a_token_from_the_cache(mock_slurmrestd_api_cache_dir):
    """
    Verifies that the token is retrieved from the cache if it is found there.
    """
    mock_slurmrestd_api_cache_dir.mkdir(parents=True)
    token_path = mock_slurmrestd_api_cache_dir / "dummy-user.token"
    one_minute_from_now = int(datetime.now(tz=timezone.utc).timestamp()) + 60
    created_token = jwt.encode(
        dict(exp=one_minute_from_now),
        key="dummy-key",
        algorithm="HS256",
    )
    token_path.write_text(created_token)
    retrieved_token = acquire_token("dummy-user")
    assert retrieved_token == created_token


@freeze_time("2022-12-01")
def test_acquire_token__gets_a_token_from_slurm_if_one_is_not_in_the_cache(
    mock_slurmrestd_api_cache_dir,
):  # noqa
    """
    Verifies that a token is pulled from Slurm if it is not found in the cache.
    Also checks to make sure the token is cached.
    """
    mock_slurmrestd_api_cache_dir.mkdir(parents=True)
    token_path = mock_slurmrestd_api_cache_dir / "dummy-user.token"
    assert not token_path.exists()

    username = "dummy-user"

    now = datetime.now()
    logger.debug(SETTINGS.SLURMRESTD_JWT_KEY_STRING)

    expected_token = jwt.encode(
        {
            "exp": int(datetime.timestamp(now + timedelta(seconds=SETTINGS.SLURMRESTD_EXP_TIME_IN_SECONDS))),
            "iat": int(datetime.timestamp(now)),
            "sun": username,
        },
        SETTINGS.SLURMRESTD_JWT_KEY_STRING,
        algorithm="HS256",
    )

    retrieved_token = acquire_token(username)
    assert retrieved_token == expected_token

    token_path = mock_slurmrestd_api_cache_dir / "dummy-user.token"
    assert token_path.read_text() == retrieved_token


@mock.patch("jobbergate_agent.identity.slurmrestd.datetime")
def test_acquire_token__uses_key_path_if_supplied(
    mocked_datetime,
    slurmrestd_jwt_key_path,
    slurmrestd_jwt_key_string,
):  # noqa
    """
    Verifies if the `acquire_token` function generates a token based
    on the key path if supplied in the Settings class.
    """

    now = datetime.now()
    username = "dummy-user"

    mocked_datetime.now = mock.Mock()
    mocked_datetime.now.return_value = now
    mocked_datetime.timestamp = mock.Mock()
    mocked_datetime.timestamp.return_value = 123

    expected_token = jwt.encode(
        {
            "exp": 123,
            "iat": 123,
            "sun": username,
        },
        slurmrestd_jwt_key_string,
        algorithm="HS256",
    )

    with mock.patch.object(SETTINGS, "SLURMRESTD_USE_KEY_PATH", new=True):
        with mock.patch.object(SETTINGS, "SLURMRESTD_JWT_KEY_PATH", new=slurmrestd_jwt_key_path):
            retrieved_token = acquire_token(username)
    assert retrieved_token == expected_token
