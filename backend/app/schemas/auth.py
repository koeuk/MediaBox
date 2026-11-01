from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ProfileUpdate(BaseModel):
    """Fields a user may change on their own account. All optional; a password
    change additionally requires the correct current_password."""

    username: str | None = Field(default=None, min_length=2, max_length=80)
    email: EmailStr | None = None
    current_password: str | None = None
    new_password: str | None = Field(default=None, min_length=6, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    username: str
    is_admin: bool
    is_premium: bool = False
    premium_until: datetime | None = None
    # fetch the picture itself from /auth/me/avatar
    has_avatar: bool = False
    has_hidden_password: bool = False
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class MediaTokenOut(BaseModel):
    token: str
    expires_in: int  # seconds


class HiddenPasswordSet(BaseModel):
    current_password: str | None = None
    new_password: str = Field(min_length=1, max_length=128)


class HiddenPasswordRemove(BaseModel):
    password: str


class HiddenPasswordVerify(BaseModel):
    password: str
