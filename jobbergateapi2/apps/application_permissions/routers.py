"""
Router for the ApplicationPermissions resource.
"""
from typing import List

from fastapi import APIRouter, Depends, Form, HTTPException, Query, status
from pydantic import ValidationError

from jobbergateapi2.apps.application_permissions.models import application_permissions_table
from jobbergateapi2.apps.application_permissions.schemas import ApplicationPermission
from jobbergateapi2.apps.auth.authentication import get_current_user
from jobbergateapi2.apps.users.schemas import User
from jobbergateapi2.compat import INTEGRITY_CHECK_EXCEPTIONS
from jobbergateapi2.storage import database

router = APIRouter()


@router.post(
    "/application-permissions/",
    status_code=status.HTTP_201_CREATED,
    description="Endpoint to create application permissions",
)
async def application_permissions_create(
    current_user: User = Depends(get_current_user),
    acl: str = Form(...),
):
    """
    Create new application permission using an admin user.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="To create permissions the user must be superuser",
        )

    try:
        permission = ApplicationPermission(acl=acl)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    async with database.transaction():
        try:
            query = application_permissions_table.insert()
            values = {"acl": acl}
            permission_created_id = await database.execute(query=query, values=values)

        except INTEGRITY_CHECK_EXCEPTIONS as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

        permission.id = permission_created_id
        return permission


@router.get(
    "/application-permissions/",
    description="Endpoint to list application permissions",
    response_model=List[ApplicationPermission],
)
async def application_permissions_list(current_user: User = Depends(get_current_user)):
    """
    List applications permissions.
    """
    query = application_permissions_table.select()
    raw_permissions = await database.fetch_all(query)
    permissions = [ApplicationPermission.parse_obj(x) for x in raw_permissions]
    return permissions


@router.delete(
    "/application-permissions/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete application permission",
)
async def application_permissions_delete(
    current_user: User = Depends(get_current_user),
    permission_id: int = Query(..., description="id of the application permission to delete"),
):
    """
    Delete application permission given its id.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="To delete permissions the user must be superuser",
        )
    where_stmt = application_permissions_table.c.id == permission_id
    get_query = application_permissions_table.select().where(where_stmt)
    raw_permission = await database.fetch_one(get_query)
    if not raw_permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ApplicationPermission {permission_id=} not found.",
        )
    delete_query = application_permissions_table.delete().where(where_stmt)
    await database.execute(delete_query)


def include_router(app):
    app.include_router(router)
