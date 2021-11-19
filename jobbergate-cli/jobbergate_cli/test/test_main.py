"""
Unit test helper functions in main
"""
import pathlib
from unittest.mock import create_autospec, patch

import click
import pytest
from pytest import fixture, mark

from jobbergate_cli import config, main


@fixture
def token_cache_mock(sample_token):
    """
    Mock access to the filesystem path where the jwt token is cached
    """
    mockpath = create_autospec(pathlib.Path, instance=True)
    mockpath.exists.return_value = True
    mockpath.read_text.return_value = sample_token
    with patch.object(config.settings, "JOBBERGATE_API_JWT_PATH", mockpath):
        yield mockpath


@fixture
def sample_token():
    """
    A sample JWT that contains info needed for auth through the jobbergate-cli.
    The token expires 2021-11-19 15:52:53.
    """
    return "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IjJtQXdkbmhGQVZ3alVuMzRJdXBzMiJ9.eyJodHRwczovL3d3dy5hcm1hZGEtaHBjLmNvbSI6eyJvcmdfbmFtZSI6Im9zbCIsInVzZXJfaWQiOiJnb29nbGUtb2F1dGgyfDEwNjI0NzY3NDY1NDE4MTMyNzkwNSIsInVzZXJuYW1lIjoidHVja2VyQG9tbml2ZWN0b3Iuc29sdXRpb25zIn0sImlzcyI6Imh0dHBzOi8vb21uaXZlY3Rvci51cy5hdXRoMC5jb20vIiwic3ViIjoiZ29vZ2xlLW9hdXRoMnwxMDYyNDc2NzQ2NTQxODEzMjc5MDUiLCJhdWQiOlsiaHR0cHM6Ly9hcm1hZGEub21uaXZlY3Rvci5zb2x1dGlvbnMiLCJodHRwczovL29tbml2ZWN0b3IudXMuYXV0aDAuY29tL3VzZXJpbmZvIl0sImlhdCI6MTYzNzI3OTU3MywiZXhwIjoxNjM3MzY1OTczLCJhenAiOiJKUWlLWnlpTldGa2FCTTVVN3VMQXA1c3FrZWdYUEpvcSIsInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgZW1haWwiLCJvcmdfaWQiOiJvcmdfS0huREFpdEc3NmVuTncxVSIsInBlcm1pc3Npb25zIjpbImRlbGV0ZTppbnZpdGF0aW9ucyIsImRlbGV0ZTp1c2VycyIsImpvYmJlcmdhdGU6YXBwbGljYXRpb25zOmNyZWF0ZSIsImpvYmJlcmdhdGU6YXBwbGljYXRpb25zOmRlbGV0ZSIsImpvYmJlcmdhdGU6YXBwbGljYXRpb25zOnJlYWQiLCJqb2JiZXJnYXRlOmFwcGxpY2F0aW9uczp1cGRhdGUiLCJyZWFkOmNvbm5lY3Rpb25zIiwicmVhZDpncmFwaHFsIiwicmVhZDppbnZpdGF0aW9ucyIsInJlYWQ6cGVybWlzc2lvbnMiLCJyZWFkOnJvbGU6cGVybWlzc2lvbnMiLCJyZWFkOnJvbGVzIiwicmVhZDp1c2VycyIsIndyaXRlOmdyYXBocWwiLCJ3cml0ZTppbnZpdGF0aW9ucyIsIndyaXRlOnVzZXJzIl19.ynZd_Selm0mwPu-RGEx3RggPySJyfuz95SWz2TBinEhBCkfxSXFmV7RVWfQnbJYttJNA6YlwswZmqMBj0Zc712D2xpAQ92KGqw58jlJzKtbjExoeJ-JRSmWJ1E4P0y5Dm_5gXCbF1OY1BeM0Z3PM_lfeakeD46V1VV0QX2dgglm3epvDGIG7_q-gvwbsFLIDN3Xw9ADsFzd79IdJNCijzeOv5-5WyTBTnkAkRqLC1Ggf3MHWIc0yvV1fSzvToY_MR7OgTsTyQHTqaEjFsMphBOHoWKo1DkAOPuTT1EXcqcsoF8X7wz9HfG5IVLDei3A7dKOM8yUdCECg1C975R5ITQ"  # noqa


@mark.parametrize(
    "use_cache,when,is_valid",
    [
        [True, "2021-11-19 00:00:00", True],
        [True, "2021-11-19 23:59:59", False],
        [False, "2021-11-19 00:00:00", True],
        [False, "2021-11-19 23:59:59", False],
    ],
    ids=[
        "cache;dwf;valid",
        "cache;dwf;expired",
        "nocache;dwf;valid",
        "nocache;dwf;expired",
    ],
)
@mark.freeze_time()
@mark.usefixtures("token_cache_mock")
def test_init_token(use_cache, when, is_valid, freezer, sample_token):
    """
    Do I successfully parse tokens from the cache or explicitly supplied? Do I identify invalid tokens?
    """
    token = sample_token if not use_cache else None
    freezer.move_to(when)
    ctx_obj = {}
    if is_valid:
        assert main.init_token(token, ctx_obj)
        assert "identity" in ctx_obj
    else:
        with pytest.raises(click.ClickException, match="The auth token is expired"):
            main.init_token(token, ctx_obj)
