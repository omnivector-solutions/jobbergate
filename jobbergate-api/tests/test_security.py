"""
Test the security module.
"""

from unittest.mock import patch

import pytest

from jobbergate_api.security import (
    HTTPException,
    IdentityPayload,
    TokenPayload,
    get_domain_configs,
    lockdown_with_identity,
    settings,
)


def test_get_domain_configs__loads_only_base_settings():
    """Check if the correct domain configuration is loaded when only one domain is provided."""
    with (
        patch.object(settings, "ARMASEC_DOMAIN", new="foo.io"),
    ):
        domain_configs = get_domain_configs()

    assert len(domain_configs) == 1
    first_config = domain_configs.pop()
    assert first_config.domain == "foo.io"


def test_get_domain_configs__loads_admin_settings_if_all_are_present():
    """Check if the correct domain configuration is loaded when two domains are provided."""
    with (
        patch.object(settings, "ARMASEC_DOMAIN", new="foo.io"),
        patch.object(settings, "ARMASEC_ADMIN_DOMAIN", new="admin.io"),
    ):
        domain_configs = get_domain_configs()

    assert len(domain_configs) == 1
    first_config = domain_configs.pop()
    assert first_config.domain == "foo.io"

    with (
        patch.object(settings, "ARMASEC_DOMAIN", new="foo.io"),
        patch.object(settings, "ARMASEC_ADMIN_DOMAIN", new="admin.io"),
        patch.object(settings, "ARMASEC_ADMIN_MATCH_KEY", new="foo"),
        patch.object(settings, "ARMASEC_ADMIN_MATCH_VALUE", new="bar"),
    ):
        domain_configs = get_domain_configs()

    assert len(domain_configs) == 2
    (first_config, second_config) = domain_configs
    assert first_config.domain == "foo.io"
    assert second_config.domain == "admin.io"
    assert second_config.match_keys == dict(foo="bar")


def test_lockdown_with_identity__success():
    """Check if the lockdown_with_identity decorator returns the correct identity."""
    token_raw_data = dict(sub="dummy-sub")
    token_payload = TokenPayload.model_validate(token_raw_data)
    lock = lockdown_with_identity()

    actual_identity = lock(token_payload)
    expected_identity = IdentityPayload.model_validate(token_raw_data)

    assert actual_identity == expected_identity


@pytest.mark.parametrize("opt_name", ["ensure_email", "ensure_organization", "ensure_client_id"])
def test_lockdown_with_identity_ensure_fields__success(opt_name):
    """Check if the lockdown_with_identity decorator returns the correct identity."""
    token_raw_data = dict(
        sub="dummy-sub",
        client_id="dummy-client-id",
        email="dummy-email@pytest.com",
        organization={
            "dummy-organization-id": {
                "name": "Dummy Organization",
                "alias": "dummy-organization",
                "attributes": {"logo": [""], "created_at": ["1689105153.0"]},
            }
        },
    )
    token_payload = TokenPayload.model_validate(token_raw_data)

    kwargs = {opt_name: True}
    lock = lockdown_with_identity(**kwargs)

    actual_identity = lock(token_payload)
    expected_identity = IdentityPayload.model_validate(token_raw_data)

    assert actual_identity == expected_identity


@pytest.mark.parametrize("opt_name", ["ensure_email", "ensure_organization", "ensure_client_id"])
def test_lockdown_with_identity_ensure_fields__raises_error(opt_name):
    """Check if the lockdown_with_identity decorator raises an error when the identity is missing a field."""
    token_raw_data = dict(sub="dummy-sub")
    token_payload = TokenPayload.model_validate(token_raw_data)
    kwargs = {opt_name: True}
    lock = lockdown_with_identity(**kwargs)

    with pytest.raises(HTTPException) as exc_info:
        lock(token_payload)
    assert exc_info.value.status_code == 400


def test_lockdown_with_identity__backward_compatibility():
    """
    Check if the lockdown_with_identity decorator returns the correct identity.

    For backwards compatibility, the organization_id is set to None if it is a string.
    """
    token_raw_data = dict(
        sub="dummy-sub",
        client_id="dummy-client-id",
        email="dummy-email@pytest.com",
        organization="dummy-organization-id",
    )
    token_payload = TokenPayload.model_validate(token_raw_data)

    lock = lockdown_with_identity()

    actual_identity = lock(token_payload)
    assert actual_identity.organization_id is None

    expected_identity = IdentityPayload.model_validate(token_raw_data)
    assert actual_identity == expected_identity


def test_lockdown_extracting_organization_id_from_new_token_structure():
    """Check if the lockdown_with_identity decorator extracts organization_id from the new token structure."""

    org_id = "cdec816e-a28a-43cd-8d75-017a700540a1"

    token_raw_data = dict(
        sub="dummy-sub",
        client_id="dummy-client-id",
        email="dummy-email@pytest.com",
        organization={
            org_id: {
                "id": org_id,
                "name": "Dummy Organization",
                "alias": "dummy-organization",
                "attributes": {"logo": [""], "created_at": ["1689105153.0"]},
            }
        },
    )
    token_payload = TokenPayload.model_validate(token_raw_data)

    lock = lockdown_with_identity()
    actual_identity = lock(token_payload)

    assert actual_identity.organization_id == org_id
