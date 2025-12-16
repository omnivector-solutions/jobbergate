"""
Instantiates armasec resources for auth on api endpoints using project settings.

Also provides a factory function for TokenSecurity to reduce boilerplate.
"""

from armasec import Armasec, TokenPayload
from armasec.schemas import DomainConfig
from armasec.token_security import PermissionMode
from buzz import check_expressions
from fastapi import Depends, HTTPException, status
from loguru import logger
from pydantic import EmailStr, model_validator

from jobbergate_api.config import settings


def get_domain_configs() -> list[DomainConfig]:
    """
    Return a list of DomainConfig objects based on the input variables for the Settings class.
    """
    # make type checkers happy
    assert settings.ARMASEC_DOMAIN is not None

    domain_configs = [
        DomainConfig(
            domain=settings.ARMASEC_DOMAIN,
            use_https=settings.ARMASEC_USE_HTTPS,
        )
    ]
    if all(
        [
            settings.ARMASEC_ADMIN_DOMAIN,
            settings.ARMASEC_ADMIN_MATCH_KEY,
            settings.ARMASEC_ADMIN_MATCH_VALUE,
        ]
    ):
        # make type checkers happy
        assert settings.ARMASEC_ADMIN_DOMAIN is not None
        assert settings.ARMASEC_ADMIN_MATCH_KEY is not None
        assert settings.ARMASEC_ADMIN_MATCH_VALUE is not None

        domain_configs.append(
            DomainConfig(
                domain=settings.ARMASEC_ADMIN_DOMAIN,
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

    email: EmailStr | None = None
    organization_id: str | None = None

    @model_validator(mode="before")
    @classmethod
    def extract_organization(cls, values):
        """
        Extract the organization_id from the organization payload.

        The payload is expected to look like:

        # Old json structure
        {
            ...,
            "organization": {
                "adf99e01-5cd5-41ac-a1af-191381ad7780": {
                    ...
                }
            }
        }

        or:

        # New json structure
        {
            ...,
            "organization": {
                "orgname": {
                    "id": "adf99e01-5cd5-41ac-a1af-191381ad7780",
                    ...
                }
            }
        }
        """

        organization_dict = values.pop("organization", None)
        if organization_dict is None or isinstance(organization_dict, str):
            # String is accepted for backwards compatibility with previous Keycloak setup
            # Code downstream ensures that the organization_id is not None if necessary
            logger.warning(f"Invalid organization payload: {organization_dict}")
            return values

        if not isinstance(organization_dict, dict):
            raise ValueError(f"Invalid organization payload: {organization_dict}")
        elif len(organization_dict) != 1:
            raise ValueError(f"Organization payload did not include exactly one value: {organization_dict}")

        org_field = next(iter(organization_dict))
        # Check if the organization field has the id field from Keycloak version
        org_id = organization_dict[org_field].get("id", org_field)

        return {**values, "organization_id": org_id}


def lockdown_with_identity(
    *scopes: str,
    permission_mode: PermissionMode = PermissionMode.SOME,
    ensure_email: bool = False,
    ensure_organization: bool = False,
    ensure_client_id: bool = False,
):
    """
    Provide a wrapper to be used with dependency injection to extract identity on a secured route.
    """

    def dependency(
        token_payload: TokenPayload = Depends(guard.lockdown(*scopes, permission_mode=permission_mode)),
    ) -> IdentityPayload:
        """
        Provide an injectable function to lockdown a route and extract the identity payload.
        """
        identity_payload = IdentityPayload(**token_payload.model_dump())

        with check_expressions(
            base_message="Access token does not contain",
            raise_exc_class=HTTPException,
            exc_builder=lambda params: params.raise_exc_class(
                status_code=status.HTTP_400_BAD_REQUEST,  # type: ignore
                detail=params.message,  # type: ignore
            ),
        ) as check:
            for ensure, name in zip(
                (ensure_email, ensure_organization, ensure_client_id),
                ("email", "organization_id", "client_id"),
            ):
                if ensure:
                    check(getattr(identity_payload, name, None) is not None, message=name)

        return identity_payload

    return dependency
