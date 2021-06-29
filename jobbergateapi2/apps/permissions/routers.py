"""
Router for the permissions resource.
"""
from typing import List

from fastapi import APIRouter, Depends, Form, HTTPException, Query, status
from fastapi_permissions import Allow, Authenticated, Deny
from pydantic import ValidationError

from jobbergateapi2.apps.auth.authentication import get_current_user
from jobbergateapi2.apps.permissions.models import (
    application_permissions_table,
    job_script_permissions_table,
    job_submission_permissions_table,
)
from jobbergateapi2.apps.permissions.schemas import (
    _ACL_RX,
    AllPermissions,
    ApplicationPermission,
    BasePermission,
    JobScriptPermission,
    JobSubmissionPermission,
)
from jobbergateapi2.apps.users.schemas import User
from jobbergateapi2.compat import INTEGRITY_CHECK_EXCEPTIONS
from jobbergateapi2.storage import database

router = APIRouter()


_QUERY_RX = r"^(application|job_script|job_submission)$"
permission_classes = {
    "application": ApplicationPermission,
    "job_script": JobScriptPermission,
    "job_submission": JobSubmissionPermission,
}
permission_tables = {
    "application": application_permissions_table,
    "job_script": job_script_permissions_table,
    "job_submission": job_submission_permissions_table,
}


async def resource_acl_as_list(permission_query):
    """
    Return the permissions as a list.
    For example:
    [(Allow|Authenticated|view), (Deny|role:troll:delete)]
    """
    permission_class = permission_classes[permission_query]
    permission_table = permission_tables[permission_query]

    query = permission_table.select()
    raw_permissions = await database.fetch_all(query)
    permissions = [permission_class.parse_obj(x) for x in raw_permissions]
    acl_list = []
    for permission in permissions:
        action, principal, permission = permission.acl.split("|")
        action_type = Deny
        if action == "Allow":
            action_type = Allow
        principal_type = principal
        if principal == "Authenticated":
            principal_type = Authenticated
        acl_list.append((action_type, principal_type, permission))
    return acl_list


@router.post(
    "/permissions/",
    status_code=status.HTTP_201_CREATED,
    description="Endpoint to create permissions",
)
async def permission_create(
    current_user: User = Depends(get_current_user),
    acl: str = Form(..., regex=_ACL_RX),
    permission_query: str = Query(..., regex=_QUERY_RX),
):
    """
    Create new permission using an admin user.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="To create permissions the user must be superuser",
        )
    permission_class = permission_classes[permission_query]
    permission_table = permission_tables[permission_query]

    try:
        permission = permission_class(acl=acl)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    async with database.transaction():
        try:
            query = permission_table.insert()
            permission_created_id = await database.execute(query=query, values={"acl": acl})

        except INTEGRITY_CHECK_EXCEPTIONS as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

        permission.id = permission_created_id
        return permission


@router.get(
    "/permissions/",
    description="Endpoint to list permissions",
    response_model=List[BasePermission],
)
async def permission_list(
    current_user: User = Depends(get_current_user),
    permission_query: str = Query(..., regex=_QUERY_RX),
):
    """
    List permissions.
    """
    permission_class = permission_classes[permission_query]
    permission_table = permission_tables[permission_query]

    query = permission_table.select()
    raw_permissions = await database.fetch_all(query)
    permissions = [permission_class.parse_obj(x) for x in raw_permissions]
    return permissions


@router.get(
    "/permissions/all",
    description="Endpoint to list permissions",
    response_model=List[AllPermissions],
)
async def permission_list_all(
    current_user: User = Depends(get_current_user),
):
    """
    List all permissions.
    """
    all_permissions = []
    for permission_query in ["application", "job_script", "job_submission"]:
        permission_class = permission_classes[permission_query]
        permission_table = permission_tables[permission_query]

        query = permission_table.select()
        raw_permissions = await database.fetch_all(query)
        for raw_permission in raw_permissions:
            permission = permission_class.parse_obj(raw_permission)
            all_permissions.append(AllPermissions(resource_name=permission_query, **permission.dict()))
    return all_permissions


@router.delete(
    "/permissions/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete permission",
)
async def permission_delete(
    current_user: User = Depends(get_current_user),
    permission_id: int = Query(..., description="id of the permission to delete"),
    permission_query: str = Query(..., regex=_QUERY_RX),
):
    """
    Delete permission given its id.
    """
    permission_class = permission_classes[permission_query]
    permission_table = permission_tables[permission_query]

    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="To delete permissions the user must be superuser",
        )
    where_stmt = permission_table.c.id == permission_id
    get_query = permission_table.select().where(where_stmt)
    raw_permission = await database.fetch_one(get_query)
    if not raw_permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{permission_class.__name__} {permission_id=} not found.",
        )
    delete_query = permission_table.delete().where(where_stmt)
    await database.execute(delete_query)


def include_router(app):
    app.include_router(router)
