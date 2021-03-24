import typing

from fastapi import APIRouter, Depends, HTTPException
from asyncpg.exceptions import UniqueViolationError

from .models import User as UserModel
from jobbergate_api.apps.auth.authentication import validate_token
from jobbergate_api.apps.users.schemas import User, UserCreate
from jobbergate_api.main import db
from jobbergate_api.pagination import Pagination

router = APIRouter()


@router.get(
    "/users/",
    description="Endpoint to search users",
    response_model=typing.List[User],
    dependencies=[Depends(validate_token)],
)
async def users_search(p: Pagination = Depends()):
    if p.q is None:
        query = UserModel.query.limit(p.limit).offset(p.offset)
    else:
        query = UserModel.query.where(UserModel.username == p.q).limit(p.limit).offset(p.offset)
    users = await query.gino.all()
    return users


@router.post("/users", description="Endpoint for user creation", dependencies=[Depends(validate_token)])
async def users_create(user_data: UserCreate):
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
