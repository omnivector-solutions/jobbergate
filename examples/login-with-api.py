"""
Demonstrate basic method of logging in via web portal and using the token to make a request to the Jobbegate API.

To run this example::

- Create a virtual environment to work in:
  $ python -m venv env

- Activate the virtual environment
  $ source env/bin/activate

- Install our two dependencies
  $ pip install httpx python-jose python-dotenv

- Run the demo
  $ python login-with-api.py


Note: Before running this demo, you will need to have the following config settings::

- ARMADA_API_BASE
- OIDC_DOMAIN
- OIDC_CLIENT_ID

These can either be set in a `.env` file or as environment variables.


Note:  If you want to use a local dev environment, you will need to follow the
instructions in the README of the `jobbergate-composed` directory to set up a local
environment using `docker-compose`. You will also need the following config settings::

- OIDC_DOMAIN=http://keycloak.local:8080/realms/jobbergate-local
- OIDC_CLIENT_ID=cli
- ARMADA_API_BASE=http://localhost:8000

Note: After logging in the first time, running this demo again will use the token saved
in the same directory as "demo.token" until that token expires.
"""

import pathlib
import os
import time

import httpx
from dotenv import load_dotenv
from jose import jwt
from jose.exceptions import ExpiredSignatureError

load_dotenv()

domain = os.getenv("OIDC_DOMAIN")
client_id = os.getenv("OIDC_CLIENT_ID")
base_api_url = os.getenv("ARMADA_API_BASE")

access_token_file = pathlib.Path("./access.token")
refresh_token_file = pathlib.Path("./refresh.token")


def is_token_expired(token):
    """
    Check a token to see if it is expired.

    Do not check any other parts of a token including its signature. The API will validate the token for us, we only
    want to see if we should first fetch a new token.
    """
    try:
        jwt.decode(token, None, options=dict(verify_signature=False, verify_aud=False, verify_exp=True))
        return False
    except ExpiredSignatureError:
        return True


def login():
    """
    Get a new access token and refresh_token by logging into the web auth portal.

    Returns a 2-tuple of (access-token, refresh-token)
    """
    response = httpx.post(
        f"{domain}/protocol/openid-connect/auth/device",
        data=dict(
            client_id=client_id,
            grant_type="client_credentials",
        ),
    )
    device_code_data = response.json()
    verification_url = device_code_data["verification_uri_complete"]
    wait_interval = device_code_data["interval"]
    device_code = device_code_data["device_code"]

    print(f"Login Here: {verification_url}")
    while True:
        time.sleep(wait_interval)
        response = httpx.post(
            f"{domain}/protocol/openid-connect/token",
            data=dict(
                grant_type="urn:ietf:params:oauth:grant-type:device_code",
                device_code=device_code,
                client_id=client_id,
            ),
        )
        try:
            response.raise_for_status()  # Will throw an exception if response isn't in 200s
            response_data = response.json()
            return (
                response_data["access_token"],
                response_data["refresh_token"],
            )
        except Exception:
            pass


def refresh(refresh_token):
    """
    Refresh an access token using a refresh token.
    """
    response = httpx.post(
        f"{domain}/protocol/openid-connect/token",
        data=dict(
            client_id=client_id,
            grant_type="refresh_token",
            refresh_token=refresh_token,
        ),
    )
    print("RESPONSE: ", response)
    refreshed_data = response.json()
    print("Refreshed data: ", refreshed_data)
    access_token = refreshed_data["access_token"]
    return access_token


def get_saved_token(token_file, check_expiration=False):
    """
    Get a token that has been saved in a file and optionally check its expriation.
    """
    if not token_file.exists():
        return None

    token = token_file.read_text().strip()
    if check_expiration and is_token_expired(token):
        return None

    return token


def acquire_token():
    """
    Acquire an access token by attempting, in order::

    * Retrieve from where it is cached in a local file
    * Refresh it with a refresh token
    * Retreive it from the auth API using client credentials
    """
    access_token = get_saved_token(access_token_file, check_expiration=True)
    if access_token is None:
        refresh_token = get_saved_token(refresh_token_file)

        if refresh_token is None:
            (access_token, refresh_token) = login()
            refresh_token_file.write_text(refresh_token)
            refresh_token_file.chmod(0o600)
        else:
            access_token = refresh(refresh_token)
        access_token_file.write_text(access_token)
        access_token_file.chmod(0o600)
    return access_token

if __name__ == '__main__':
    token = acquire_token()

    response = httpx.get(
        f"{base_api_url}/jobbergate/job-submissions",
        headers=dict(Authorization=f"Bearer {token}"),
    )
    try:
        response.raise_for_status()
        print("Successfully logged in!")
    except Exception as err:
        print(f"Login failed: {err}")
