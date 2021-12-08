"""
Instantiates armada-security resources for auth on api endpoints using project settings.
Also provides a factory function for TokenSecurity to reduce boilerplate.
"""
from typing import Optional

from armasec import Armasec, TokenPayload
from loguru import logger
from pydantic import BaseModel, EmailStr

from jobbergate_api.config import settings

guard = Armasec(
    settings.ARMASEC_DOMAIN,
    audience=settings.ARMASEC_AUDIENCE,
    debug_logger=logger.debug if settings.ARMASEC_DEBUG else None,
)


class ArmadaClaims(BaseModel):
    org_name: Optional[str]
    user_email: EmailStr

    @classmethod
    def from_token_payload(cls, payload: TokenPayload) -> "ArmadaClaims":
        """
        Creates an instance of ArmadaClaims from a Token payload. Automatically validates that the
        user_email is present and is an email address
        """
        return cls(**getattr(payload, settings.ARMADA_CLAIMS_KEY))
