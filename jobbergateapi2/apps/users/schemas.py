"""
Defines the schema for the resource User
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field

pwd_context = CryptContext(
    schemes=["pbkdf2_sha512"], deprecated="auto", pbkdf2_sha512__rounds=500_000, pbkdf2_sha512__salt_size=64
)


class User(BaseModel):
    """
    Base model for the resource User, defining the default attributes and used for auto generated docs
    """

    id: Optional[UUID] = Field(None)
    email: EmailStr
    is_active: Optional[bool] = Field(True)
    is_admin: Optional[bool] = Field(False)
    username: str = Field(..., max_length=64, description="The name that represents the user")
    data_joined: Optional[datetime] = Field(None)

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "username": "someusername",
                "email": "user@email.com",
                "password": "f1edef6a67e7445c8c88d189fd7ff63b",
            }
        }

    def __str__(self):
        return f"{self.id}, {self.username}, {self.email}"


class UserCreate(User):
    """
    Class used defines that a User have a password and garantee that it is hashed
    """

    password: str = Field(
        None, min_length=12, max_length=100, description="Password with length between 12 and 100 characters"
    )

    def hash_password(self):
        """
        Function used to hash a password using pbkdf2
        """
        if not self.password:
            return

        return pwd_context.hash(self.password)
