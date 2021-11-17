"""
Unit test helper functions in main
"""
import json
import pathlib
from unittest.mock import create_autospec, patch

from pytest import fixture, mark

from jobbergate_cli import main


@fixture
def token_cache_mock(dwf_jwt_token):
    """
    Mock access to the filesystem path where the jwt token is cached
    """
    mockpath = create_autospec(pathlib.Path, instance=True)
    mockpath.exists.return_value = True
    mockpath.read_text.return_value = dwf_jwt_token["raw"]
    with patch.object(main, "JOBBERGATE_API_JWT_PATH", mockpath):
        yield mockpath


@fixture
def dwf_jwt_token():
    """
    A token as presented by the deprecated DWF JWT, through the API
    """
    token_data = {
        "token": (
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjo0OC"
            "widXNlcm5hbWUiOiJjb3J5LmRvZHRAb21uaXZlY3Rvci5zb2x1dGlvb"
            "nMiLCJleHAiOjE2MDYxNjEwMDcsImVtYWlsIjoiY29yeS5kb2R0QG9t"
            "bml2ZWN0b3Iuc29sdXRpb25zIn0.ckuL-9-UDxNucT_mETYIrA7ku9Q"
            "FpArvLFf3X4VT4Uw"
        )
    }
    return {"raw": token_data["token"], "encoded": json.dumps(token_data)}


@fixture
def dwf_jwt_token_response(dwf_jwt_token, response_mock):
    return response_mock(
        f"""
            POST https://jobbergate-api-staging.omnivector.solutions/token/

            -> 200 :{dwf_jwt_token["encoded"]}
            """
    )


# @fixture
# def simplejwt_token():
#     """
#     A token as presented by simplejwt through the API
#     """
#     token_data = {
#           "access": (
#               "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX3BrIjoxLCJ0"
#               "b2tlbl90eXBlIjoiYWNjZXNzIiwiY29sZF9zdHVmZiI6IuKYgyIsImV4c"
#               "CI6MTIzNDU2LCJqdGkiOiJmZDJmOWQ1ZTFhN2M0MmU4OTQ5MzVlMzYyYm"
#               "NhOGJjYSJ9.NHlztMGER7UADHZJlxNG0WSi22a2KaYSfd1S-AuT7lU"),
#           "refresh": (
#               "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX3BrIjoxLCJ0b"
#               "2tlbl90eXBlIjoicmVmcmVzaCIsImNvbGRfc3R1ZmYiOiLimIMiLCJleHA"
#               "iOjIzNDU2NywianRpIjoiZGUxMmY0ZTY3MDY4NDI3ODg5ZjE1YWMyNzcwZ"
#               "GEwNTEifQ.aEoAYkSJjoWH1boshQAaTkf8G3yn0kapko6HFRt7Rh4"),
#           }
#     return {
#         "raw": token_data['access'],
#         "encoded": json.dumps(token_data),
#     }


@mark.parametrize(
    "token_responder_name,when,is_valid",
    [
        ["dwf_jwt_token_response", "2020-11-23 19:50:00", True],
        ["dwf_jwt_token_response", "2022-11-23 19:50:00", False],
        # ["simplejwt_token_response", "1970-01-02 09:17:59", True],
    ],
    ids=[
        "dwf;valid",
        "dwf;expired",
        # simplejwt;valid
    ],
)
@mark.freeze_time()
def test_init_token(token_responder_name, when, is_valid, freezer, token_cache_mock, request):
    """
    Do I successfully parse various tokens? Do I identify invalid tokens?
    """
    token_responder = request.getfixturevalue(token_responder_name)
    freezer.move_to(when)
    with token_responder:
        main.init_token("unittests@omnivector.solutions", "unit tests")
        assert bool(main.is_token_valid()) == is_valid
