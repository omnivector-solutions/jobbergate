"""
Application that holds the authentication process using JWT token
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi_permissions import Authenticated, Everyone, configure_permissions
from jose import JWTError, jwt

from jobbergateapi2.apps.users.models import users_table
from jobbergateapi2.apps.users.schemas import User, pwd_context
from jobbergateapi2.config import settings
from jobbergateapi2.storage import database

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=settings.TOKEN_URL)

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def validate_token(token: str = Depends(oauth2_scheme)):
    """
    Given a token check if it is valid
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        return email
    except JWTError:
        raise credentials_exception


async def get_current_user(email: str = Depends(validate_token)):
    """
    Return the user of the token
    """
    query = users_table.select().where(users_table.c.email == email)
    user = User.parse_obj(await database.fetch_one(query))
    return user


def get_active_principals(user: User = Depends(get_current_user)):
    if user:
        principals = user.principals.split("|") if user.principals != "" else []
        principals.extend([Everyone, Authenticated])
    else:
        principals = [Everyone]
    return principals


Permission = configure_permissions(get_active_principals)


async def authenticate_user(form_data):
    """
    Try to authenticate the user using form_data email and password, raises 401 otherwise
    """
    query = users_table.select().where(users_table.c.email == form_data.username)
    user = await database.fetch_one(query)
    exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        if not user or not pwd_context.verify(form_data.password, user["password"]):
            raise exception
    except ValueError:
        raise exception
    return user


class Token:
    """
    Class used to create and manage a JWT token for an authenticated user
    """

    def __init__(self, user):
        self.user = user

    def create(self):
        """
        Function used to create a token with default expiration time
        """
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self._create_access_token(
            data={"sub": self.user["email"]}, expires_delta=access_token_expires
        )

        return {"access_token": access_token, "token_type": "bearer"}

    def _create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """
        Given the user data and a expiration time, creates a encoded JWT token
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
