"""
Test the schema of the resource Permission.
"""
import pytest
from pydantic import ValidationError

from jobbergateapi2.apps.permissions.schemas import (
    _ACL_RX,
    _RESOURCE_RX,
    AllPermissions,
    ApplicationPermission,
    JobScriptPermission,
    JobSubmissionPermission,
)


def test_acl_regex():
    """
    Check if the _ACL_RX is correct.
    """
    assert _ACL_RX == r"^(Allow|Deny)\|(role:\w+|Authenticated)\|\w+$"


def test_resource_regex():
    assert _RESOURCE_RX == r"^(application|job_script|job_submission)$"


@pytest.mark.parametrize(
    "permission_class", [(ApplicationPermission), (JobScriptPermission), (JobSubmissionPermission)]
)
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
def test_create_permission_bad_acl(acl, permission_class):
    """
    Test that is not possible to create a Permission with the wrong format.
    """
    with pytest.raises(ValidationError):
        permission_class(acl=acl)


@pytest.mark.parametrize(
    "permission_class", [(ApplicationPermission), (JobScriptPermission), (JobSubmissionPermission)]
)
@pytest.mark.parametrize(
    "acl",
    [
        ("Deny|role:admin|delete"),
        ("Allow|Authenticated|view"),
        ("Deny|role:troll|create"),
    ],
)
def test_create_permission(acl, permission_class):
    """
    Test multiple allowed formats to create Permission.
    """
    permission = permission_class(acl=acl)
    assert permission is not None
    assert permission.acl == acl


@pytest.mark.parametrize(
    "resource_name",
    [
        ("application"),
        ("job_script"),
        ("job_submission"),
    ],
)
@pytest.mark.parametrize(
    "acl",
    [
        ("Deny|role:admin|delete"),
        ("Allow|Authenticated|view"),
        ("Deny|role:troll|create"),
    ],
)
def test_create_all_permission(acl, resource_name):
    """
    Test all the allowed formats for the resource_name in the AllPermission schema.
    """
    permission = AllPermissions(resource_name=resource_name, acl=acl)

    assert permission is not None
    assert permission.acl == acl
    assert permission.resource_name == resource_name


@pytest.mark.parametrize(
    "resource_name",
    [
        ("applications"),
        ("job"),
        ("submission"),
        ("app"),
        ("bla"),
    ],
)
@pytest.mark.parametrize(
    "acl",
    [
        ("Deny|role:admin|delete"),
        ("Allow|Authenticated|view"),
        ("Deny|role:troll|create"),
    ],
)
def test_create_all_permission_bad_name(acl, resource_name):
    """
    Test that is not possible to create AllPermissions with wrong resource_name.
    """
    with pytest.raises(ValidationError):
        AllPermissions(acl=acl, resource_name=resource_name)
