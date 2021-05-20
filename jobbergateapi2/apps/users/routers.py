"""
Router for the User resource.
"""
import typing

from fastapi import APIRouter, Depends, HTTPException, Query, status

from jobbergateapi2.apps.auth.authentication import get_current_user, validate_token
from jobbergateapi2.apps.users.models import users_table
from jobbergateapi2.apps.users.schemas import User, UserCreate
from jobbergateapi2.compat import INTEGRITY_CHECK_EXCEPTIONS
from jobbergateapi2.pagination import Pagination
from jobbergateapi2.storage import database

router = APIRouter()


@router.get(
    "/users/",
    description="Endpoint to list users",
    response_model=typing.List[User],
    dependencies=[Depends(validate_token)],
)
async def users_list(p: Pagination = Depends()):
    """
    Return all the users.
    """
    query = users_table.select().limit(p.limit).offset(p.skip)
    raw_users = await database.fetch_all(query)
    users = [User.parse_obj(x) for x in raw_users]
    return users


@router.get(
    "/users/{user_id}",
    description="Endpoint to get user given the id",
    response_model=User,
    dependencies=[Depends(validate_token)],
)
async def users_get(user_id: int = Query(...)):
    """
    Return the user given it's id.
    """
    query = users_table.select(users_table.c.id == user_id)
    raw_user = await database.fetch_one(query)
    if not raw_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id=} not found",
        )
    user = User.parse_obj(raw_user)
    return user


@router.get(
    "/user/me",
    description="Endpoint to get current user",
    response_model=User,
)
async def users_me(current_user: User = Depends(get_current_user)):
    """
    Return the authenticated user.
    """
    return current_user


@router.post("/users/", description="Endpoint for user creation", dependencies=[Depends(validate_token)])
async def users_create(user_data: UserCreate):
    """
    Create new users.
    """
    async with database.transaction():
        try:
            query = users_table.insert()
            values = {
                "full_name": user_data.full_name,
                "email": user_data.email,
                "password": user_data.hash_password(),
                "is_superuser": user_data.is_superuser,
                "is_active": user_data.is_active,
            }
            user_created_id = await database.execute(query=query, values=values)

        except INTEGRITY_CHECK_EXCEPTIONS as e:
            raise HTTPException(status_code=422, detail=str(e))
    return user_created_id


def include_router(app):
    app.include_router(router)
