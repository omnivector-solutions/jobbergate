"""
Instantiates armasec resources for auth on api endpoints using project settings.

Also provides a factory function for TokenSecurity to reduce boilerplate.
"""
from typing import List, Optional

from armasec import Armasec, TokenPayload
from armasec.schemas import DomainConfig
from armasec.token_security import PermissionMode
from fastapi import Depends
from loguru import logger
from pydantic import EmailStr, root_validator

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


class IdentityPayload(TokenPayload):
    """
    Provide an extension of TokenPayload that includes the user's identity.
    """

    email: Optional[EmailStr] = None
    organization_id: Optional[str] = None

    @root_validator(pre=True)
    def extract_organization(cls, values):
        """
        Extract the organization_id from the organization payload.

        The payload is expected to look like when the incoming request is from an organization user:
        {
            ...,
            "organization": {
                "adf99e01-5cd5-41ac-a1af-191381ad7780": {
                    ...
                }
            }
        }

        The payload is expected to look like when the incoming request is from an agent:
        {
            ...,
            "organization": "adf99e01-5cd5-41ac-a1af-191381ad7780",
            ...
        }
        """
        organization_payload = values.pop("organization", None)
        if organization_payload is None:
            return values

        if not isinstance(organization_payload, dict) or not isinstance(organization_payload, str):
            raise ValueError(f"Invalid organization payload: {organization_payload}")
        elif len(organization_payload) != 1 and isinstance(organization_payload, dict):
            raise ValueError(
                f"Organization payload did not include exactly one value: {organization_payload}"
            )
        return {
            **values,
            "organization_id": next(iter(organization_payload))
            if isinstance(organization_payload, dict)
            else organization_payload,
        }


def lockdown_with_identity(*scopes: str, permission_mode: PermissionMode = PermissionMode.ALL):
    """
    Provide a wrapper to be used with dependency injection to extract identity on a secured route.
    """

    def dependency(
        token_payload: TokenPayload = Depends(guard.lockdown(*scopes, permission_mode=permission_mode))
    ) -> IdentityPayload:
        """
        Provide an injectable function to lockdown a route and extract the identity payload.
        """
        return IdentityPayload.parse_obj(token_payload)

    return dependency
