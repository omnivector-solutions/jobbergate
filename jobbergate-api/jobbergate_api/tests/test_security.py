"""
Test the security module.
"""
from datetime import datetime

import pytest
from armasec import TokenPayload
from pydantic import ValidationError

from jobbergate_api.security import IdentityPayload, get_domain_configs


def test_get_domain_configs__loads_only_base_settings(tweak_settings):
    """Check if the correct domain configuration is loaded when only one domain is provided."""
    with tweak_settings(
        ARMASEC_DOMAIN="foo.io",
        ARMASEC_AUDIENCE="https://bar.dev",
    ):
        domain_configs = get_domain_configs()

    assert len(domain_configs) == 1
    first_config = domain_configs.pop()
    assert first_config.domain == "foo.io"
    assert first_config.audience == "https://bar.dev"


def test_get_domain_configs__loads_admin_settings_if_all_are_present(tweak_settings):
    """Check if the correct domain configuration is loaded when two domains are provided."""
    with tweak_settings(
        ARMASEC_DOMAIN="foo.io",
        ARMASEC_AUDIENCE="https://bar.dev",
        ARMASEC_ADMIN_DOMAIN="admin.io",
    ):
        domain_configs = get_domain_configs()

    assert len(domain_configs) == 1
    first_config = domain_configs.pop()
    assert first_config.domain == "foo.io"
    assert first_config.audience == "https://bar.dev"

    with tweak_settings(
        ARMASEC_DOMAIN="foo.io",
        ARMASEC_AUDIENCE="https://bar.dev",
        ARMASEC_ADMIN_DOMAIN="admin.io",
        ARMASEC_ADMIN_AUDIENCE="https://admin.dev",
        ARMASEC_ADMIN_MATCH_KEY="foo",
        ARMASEC_ADMIN_MATCH_VALUE="bar",
    ):
        domain_configs = get_domain_configs()

    assert len(domain_configs) == 2
    (first_config, second_config) = domain_configs
    assert first_config.domain == "foo.io"
    assert first_config.audience == "https://bar.dev"
    assert second_config.domain == "admin.io"
    assert second_config.audience == "https://admin.dev"
    assert second_config.match_keys == dict(foo="bar")


def test_from_token_payload__omits_email_if_not_in_payload():
    """Check if omiting email causes a failure in from_token_payload()."""
    payload = TokenPayload(
        sub="dummy",
        permissions=[],
        exp=datetime.now(),
        azp="idiot",
    )
    identity = IdentityPayload.parse_obj(payload)
    assert identity.email is None


def test_identity_payload__extracts_organization_id_successfully():
    """Check if the organization_id is successfully extracted from the token payload."""
    token_payload = {
        "exp": 1689105153,
        "sub": "dummy-sub",
        "azp": "dummy-client-id",
        "organization": {
            "dummy-organization-id": {
                "name": "Dummy Organization",
                "attributes": {"logo": [""], "created_at": ["1689105153.0"]},
            }
        },
    }
    identity = IdentityPayload(**token_payload)
    assert identity.organization_id == "dummy-organization-id"


def test_identity_payload__fails_validation_with_non_dict_organization():
    """Check IdentityPayload validation fails if the organization claim is not a dict."""
    token_payload = {
        "exp": 1689105153,
        "sub": "dummy-sub",
        "azp": "dummy-client-id",
        "organization": "dummy-organization-id",
    }
    with pytest.raises(ValidationError, match="Invalid organization payload"):
        IdentityPayload(**token_payload)


def test_identity_payload__fails_validation_with_wrong_number_of_organization_values():
    """Check IdentityPayload validation fails if the organization claim does not have exactly one value."""
    token_payload = {
        "exp": 1689105153,
        "sub": "dummy-sub",
        "azp": "dummy-client-id",
        "organization": {
            "dummy-organization-id": {
                "name": "Dummy Organization",
                "attributes": {"logo": [""], "created_at": ["1689105153.0"]},
            },
            "stupid-organization-id": {
                "name": "Stupid Organization",
                "attributes": {"logo": [""], "created_at": ["1689105153.0"]},
            },
        },
    }
    with pytest.raises(ValidationError, match="Organization payload did not include exactly one value"):
        IdentityPayload(**token_payload)

    token_payload = {
        "exp": 1689105153,
        "sub": "dummy-sub",
        "azp": "dummy-client-id",
        "organization": {},
    }
    with pytest.raises(ValidationError, match="Organization payload did not include exactly one value"):
        IdentityPayload(**token_payload)


def test_identity_payload__null_organization_id_with_no_organization_claim():
    """Check IdentityPayload validation does not fail if the organization claim is not present."""
    token_payload = {
        "exp": 1689105153,
        "sub": "dummy-sub",
        "azp": "dummy-client-id",
    }
    identity = IdentityPayload(**token_payload)
    assert identity.organization_id is None
