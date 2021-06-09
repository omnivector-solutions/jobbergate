"""
Defines the schema for the resource User
"""
from datetime import datetime
from typing import Optional

from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field

pwd_context = CryptContext(
    schemes=["pbkdf2_sha512"], deprecated="auto", pbkdf2_sha512__rounds=500_000, pbkdf2_sha512__salt_size=64
)


class User(BaseModel):
    """
    Base model for the resource User, defining the default attributes and used for auto generated docs
    """

    id: Optional[int] = Field(None)
    email: EmailStr = Field(..., description="User unique email")
    is_active: Optional[bool] = Field(True)
    is_superuser: Optional[bool] = Field(False)
    full_name: str = Field(..., description="Full name of the user")
    data_joined: Optional[datetime] = Field(datetime.utcnow())

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "full_name": "first last",
                "email": "user@email.com",
                "password": "f1edef6a67e7445c8c88d189fd7ff63b",
                "is_active": True,
                "is_superser": False,
            }
        }

    def __str__(self):
        return f"{self.id}, {self.full_name}, {self.email}"


class UserCreate(User):
    """
    Class used defines that a User have a password and garantee that it is hashed
    """

    password: str = Field(
        None, min_length=12, max_length=100, description="Password with length between 12 and 100 characters"
    )
    principals: Optional[str] = Field("", description="String separated by |")

    def hash_password(self):
        """
        Function used to hash a password using pbkdf2
        """
        if not self.password:
            return

        return pwd_context.hash(self.password)
