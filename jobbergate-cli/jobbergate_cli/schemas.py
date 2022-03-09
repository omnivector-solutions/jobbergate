"""
Provide Pydantic models for various data items.
"""

from typing import Any, Dict, List, Optional

import httpx
import pydantic


class TokenSet(pydantic.BaseModel, extra=pydantic.Extra.ignore):
    """
    A model representing a pairing of access and refresh tokens
    """

    access_token: str
    refresh_token: Optional[str] = None


class IdentityData(pydantic.BaseModel):
    """
    A model representing the fields that should appear in our custom identity data claim.
    """

    user_email: str
    org_name: Optional[str]


class Persona(pydantic.BaseModel):
    """
    A model representing a pairing of a TokenSet and Identity data.
    This is a convenience to combine all of the identifying data and credentials for a given user.
    """

    token_set: TokenSet
    identity_data: IdentityData


class DeviceCodeData(pydantic.BaseModel, extra=pydantic.Extra.ignore):
    """
    A model representing the data that is returned from Auth0's device code endpoint.
    """

    device_code: str
    # verification_uri_complete: pydantic.HttpUrl
    verification_uri_complete: str
    interval: int


class JobbergateContext(pydantic.BaseModel, arbitrary_types_allowed=True):
    """
    A data object describing context passed from the main entry point.
    """

    persona: Optional[Persona]
    full_output: bool = False
    raw_output: bool = False
    client: Optional[httpx.Client]


class Pagination(pydantic.BaseModel):
    """
    A model describing the structure of the pagination component of a ListResponseEnvelope.
    """

    total: int
    start: Optional[int]
    limit: Optional[int]


class ListResponseEnvelope(pydantic.BaseModel):
    """
    A model describing the structure of response envelopes from "list" endpoints.
    """

    results: List[Dict[str, Any]]
    pagination: Pagination
