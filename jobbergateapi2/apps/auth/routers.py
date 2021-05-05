"""
Router for the auth module
"""
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from jobbergateapi2.apps.auth.authentication import Token, authenticate_user

router = APIRouter()


@router.post("/token/")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Endpoint used to auth the user via email and password and returns a token
    """
    user = await authenticate_user(form_data)
    token = Token(user)
    return token.create()


def include_router(app):
    app.include_router(router)
