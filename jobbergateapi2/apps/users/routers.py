"""
Router for the User resource
"""
import typing

from asyncpg.exceptions import UniqueViolationError
from fastapi import APIRouter, Depends, HTTPException

from .models import User as UserModel
from jobbergateapi2.apps.auth.authentication import validate_token
from jobbergateapi2.apps.users.schemas import User, UserCreate
from jobbergateapi2.main import db
from jobbergateapi2.pagination import Pagination

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
        query = UserModel.query.limit(p.limit).offset(p.offset)
    else:
        query = UserModel.query.where(UserModel.username == p.q).limit(p.limit).offset(p.offset)
    users = await query.gino.all()
    return users


@router.post("/users", description="Endpoint for user creation", dependencies=[Depends(validate_token)])
async def users_create(user_data: UserCreate):
    """
    Endpoint used to create new users using a user already authenticated
    """
    async with db.transaction():
        try:
            user_created = await UserModel.create(
                username=user_data.username,
                email=user_data.email,
                password=user_data.hash_password(),
                is_admin=user_data.is_admin,
                is_active=user_data.is_active,
            )

        except UniqueViolationError as e:
            raise HTTPException(status_code=422, detail=e.detail)
    return user_created.id


def include_router(app):
    app.include_router(router)
