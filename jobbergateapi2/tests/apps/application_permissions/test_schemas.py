"""
Test the schema of the resource ApplicationPermission
"""
import pytest
from pydantic import ValidationError

from jobbergateapi2.apps.application_permissions.schemas import ApplicationPermission


@pytest.mark.parametrize(
    "acl",
    [
        ("Deny|role|update"),
        ("Deny"),
        ("Allow|update"),
        ("Allow|role:admin"),
        ("Allow|admin|view|"),
        ("Allow|role:admin|view|"),
        ("Den|role:admin|view"),
    ],
)
def test_create_application_permission_bad_acl(acl):
    with pytest.raises(ValidationError):
        ApplicationPermission(acl=acl)


@pytest.mark.parametrize(
    "acl",
    [
        ("Deny|role:admin|delete"),
        ("Allow|Authenticated|view"),
        ("Deny|role:troll|create"),
    ],
)
def test_create_application_permission(acl):
    permission = ApplicationPermission(acl=acl)
    assert permission is not None
    assert permission.acl == acl
