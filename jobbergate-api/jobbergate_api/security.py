"""
Instantiates armasec resources for auth on api endpoints using project settings.

Also provides a factory function for TokenSecurity to reduce boilerplate.
"""
from typing import List, Optional

from armasec import Armasec, TokenPayload
from armasec.schemas import DomainConfig
from loguru import logger
from pydantic import BaseModel, EmailStr

from jobbergate_api.config import settings


def get_domain_configs() -> List[DomainConfig]:
    """
    Return a list of DomainConfig objects based on the input variables for the Settings class.
    """
    domain_configs = [
        DomainConfig(
            domain=settings.ARMASEC_DOMAIN,
            audience=settings.ARMASEC_AUDIENCE,
            use_https=settings.ARMASEC_USE_HTTPS,
        )
    ]
    if all(
        [
            settings.ARMASEC_ADMIN_DOMAIN,
            settings.ARMASEC_ADMIN_AUDIENCE,
            settings.ARMASEC_ADMIN_MATCH_KEY,
            settings.ARMASEC_ADMIN_MATCH_VALUE,
        ]
    ):
        domain_configs.append(
            DomainConfig(
                domain=settings.ARMASEC_ADMIN_DOMAIN,
                audience=settings.ARMASEC_ADMIN_AUDIENCE,
                use_https=settings.ARMASEC_USE_HTTPS,
                match_keys={settings.ARMASEC_ADMIN_MATCH_KEY: settings.ARMASEC_ADMIN_MATCH_VALUE},
            )
        )
    return domain_configs


guard = Armasec(
    domain_configs=get_domain_configs(),
    debug_logger=logger.debug if settings.ARMASEC_DEBUG else None,
)


class IdentityClaims(BaseModel):
    """
    Provide a pydantic data model containing user data extracted from an access token.
    """

    email: Optional[EmailStr]
    client_id: Optional[str]

    @classmethod
    def from_token_payload(cls, payload: TokenPayload) -> "IdentityClaims":
        """
        Create an instance from a Token payload.

        Automatically validates that the email is an email address if it is provided.
        """
        init_kwargs = dict(
            client_id=payload.client_id,
        )
        email = getattr(payload, "email", None)
        if email is not None:
            init_kwargs.update(email=email)
        return cls(**init_kwargs)
