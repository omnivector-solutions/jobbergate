"""
Router for the User resource
"""
import typing

from fastapi import APIRouter, Depends, HTTPException

from jobbergateapi2.apps.auth.authentication import validate_token
from jobbergateapi2.apps.users.models import users_table
from jobbergateapi2.apps.users.schemas import User, UserCreate
from jobbergateapi2.compat import INTEGRITY_CHECK_EXCEPTIONS
from jobbergateapi2.pagination import Pagination
from jobbergateapi2.storage import database

router = APIRouter()


@router.get(
    "/users/",
    description="Endpoint to search users",
    response_model=typing.List[User],
    dependencies=[Depends(validate_token)],
)
async def users_search(p: Pagination = Depends()):
    """
    Endpoint that requires authentication and is used to GET the users and returns using pagination
    """
    if p.q is None:
        query = users_table.select().limit(p.limit).offset(p.offset)
    else:
        query = users_table.select().where(users_table.c.username == p.q).limit(p.limit).offset(p.offset)
    users = await database.fetch_all(query)
    return users


@router.post("/users/", description="Endpoint for user creation", dependencies=[Depends(validate_token)])
async def users_create(user_data: UserCreate):
    """
    Endpoint used to create new users using a user already authenticated
    """
    async with database.transaction():
        try:
            query = users_table.insert()
            values = {
                "username": user_data.username,
                "email": user_data.email,
                "password": user_data.hash_password(),
                "is_admin": user_data.is_admin,
            }
            user_created_id = await database.execute(query=query, values=values)

        except INTEGRITY_CHECK_EXCEPTIONS as e:
            raise HTTPException(status_code=422, detail=str(e))
    return user_created_id


def include_router(app):
    app.include_router(router)
