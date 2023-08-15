from datetime import datetime, timedelta, timezone
from unittest import mock

from freezegun import freeze_time
from jose import jwt

from jobbergate_agent.identity.slurmrestd import SETTINGS, _load_token_from_cache, _write_token_to_cache, acquire_token
from jobbergate_agent.utils.logging import logger


def test__write_token_to_cache__caches_a_token(mock_slurmrestd_api_cache_dir):
    """
    Verifies that the auth token can be saved in the cache.
    """
    mock_slurmrestd_api_cache_dir.mkdir(parents=True)
    _write_token_to_cache("dummy-token", "dummy-user")
    token_path = mock_slurmrestd_api_cache_dir / "dummy-user.token"
    assert token_path.exists()
    assert token_path.read_text() == "dummy-token"


def test__write_token_to_cache__creates_cache_directory_if_does_not_exist(
    mock_slurmrestd_api_cache_dir,
):  # noqa
    """
    Verifies that the cache directory will be created if it does not already exist.
    """
    assert not mock_slurmrestd_api_cache_dir.exists()
    _write_token_to_cache("dummy-token", "dummy-user")
    assert mock_slurmrestd_api_cache_dir.exists()


def test__load_token_from_cache__loads_token_data_from_the_cache(
    mock_slurmrestd_api_cache_dir,
    slurmrestd_jwt_key_path,
    slurmrestd_jwt_key_string,
):
    """
    Verifies that a token can be retrieved from the cache.
    """
    mock_slurmrestd_api_cache_dir.mkdir(parents=True)
    token_path = mock_slurmrestd_api_cache_dir / "dummy-user.token"
    one_minute_from_now = int(datetime.now(tz=timezone.utc).timestamp()) + 60
    created_token = jwt.encode(
        dict(exp=one_minute_from_now),
        key=slurmrestd_jwt_key_string,
        algorithm="HS256",
    )
    token_path.write_text(created_token)
    with mock.patch.object(SETTINGS, "SLURMRESTD_USE_KEY_PATH", new=True):
        with mock.patch.object(SETTINGS, "SLURMRESTD_JWT_KEY_PATH", new=slurmrestd_jwt_key_path):
            retrieved_token = _load_token_from_cache("dummy-user")
    assert retrieved_token == created_token


def test__load_token_from_cache__returns_none_if_cached_token_does_not_exist(
    mock_slurmrestd_api_cache_dir,
):  # noqa
    """
    Verifies that None is returned if the cached token does not exist.
    """
    mock_slurmrestd_api_cache_dir.mkdir(parents=True)
    retrieved_token = _load_token_from_cache("dummy-user")
    assert retrieved_token is None


def test__load_token_from_cache__returns_none_if_cached_token_cannot_be_read(
    mock_slurmrestd_api_cache_dir,
):
    """
    Verifies that None is returned if the token cannot be read.
    """
    mock_slurmrestd_api_cache_dir.mkdir(parents=True)
    token_path = mock_slurmrestd_api_cache_dir / "dummy-user.token"
    token_path.write_text("pre-existing data")
    token_path.chmod(0o000)

    retrieved_token = _load_token_from_cache("dummy-user")

    assert retrieved_token is None


def test__load_token_from_cache__returns_none_if_cached_token_is_expired(
    mock_slurmrestd_api_cache_dir,
    slurmrestd_jwt_key_path,
    slurmrestd_jwt_key_string,
):  # noqa
    """
    Verifies that None is returned if the token is expired.
    """
    mock_slurmrestd_api_cache_dir.mkdir(parents=True)
    token_path = mock_slurmrestd_api_cache_dir / "dummy-user.token"
    one_second_ago = int(datetime.now(tz=timezone.utc).timestamp()) - 1
    expired_token = jwt.encode(dict(exp=one_second_ago), key=slurmrestd_jwt_key_string, algorithm="HS256")
    token_path.write_text(expired_token)

    with mock.patch.object(SETTINGS, "SLURMRESTD_USE_KEY_PATH", new=True):
        with mock.patch.object(SETTINGS, "SLURMRESTD_JWT_KEY_PATH", new=slurmrestd_jwt_key_path):
            retrieved_token = _load_token_from_cache("dummy-user")

    assert retrieved_token is None


def test__load_token_from_cache__returns_none_cached_token_will_expire_soon(
    mock_slurmrestd_api_cache_dir,
    slurmrestd_jwt_key_path,
    slurmrestd_jwt_key_string,
):
    """
    Verifies that None is returned if the token will expired soon.
    """
    mock_slurmrestd_api_cache_dir.mkdir(parents=True)
    token_path = mock_slurmrestd_api_cache_dir / "dummy-user.token"
    nine_seconds_from_now = int(datetime.now(tz=timezone.utc).timestamp()) + 9
    expired_token = jwt.encode(dict(exp=nine_seconds_from_now), key=slurmrestd_jwt_key_string, algorithm="HS256")
    token_path.write_text(expired_token)

    with mock.patch.object(SETTINGS, "SLURMRESTD_USE_KEY_PATH", new=True):
        with mock.patch.object(SETTINGS, "SLURMRESTD_JWT_KEY_PATH", new=slurmrestd_jwt_key_path):
            retrieved_token = _load_token_from_cache("dummy-user")

    assert retrieved_token is None


def test__load_token_from_cache__returns_none_if_token_is_malformed(
    mock_slurmrestd_api_cache_dir,
    slurmrestd_jwt_key_path,
):
    """
    Verifies that None is returned if the token has invalid claims.
    """
    mock_slurmrestd_api_cache_dir.mkdir(parents=True)
    token_path = mock_slurmrestd_api_cache_dir / "dummy-user.token"
    token_path.write_text("not-a-valid-jwt")

    with mock.patch.object(SETTINGS, "SLURMRESTD_USE_KEY_PATH", new=True):
        with mock.patch.object(SETTINGS, "SLURMRESTD_JWT_KEY_PATH", new=slurmrestd_jwt_key_path):
            retrieved_token = _load_token_from_cache("dummy-user")

    assert retrieved_token is None


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
