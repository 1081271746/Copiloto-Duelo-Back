from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator


Password = Annotated[str, StringConstraints(min_length=12, max_length=128)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Country = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class RegisterInput(StrictModel):
    email: EmailStr
    password: Password
    name: Name
    country: Country = "CO"

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.lower()


class LoginInput(StrictModel):
    email: EmailStr
    password: Annotated[str, StringConstraints(min_length=1, max_length=128)]


class ProfileUpdate(StrictModel):
    name: Name | None = None
    country: Country | None = None

    @field_validator("name", "country")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("null_not_allowed")
        return value


class PasswordChange(StrictModel):
    current_password: Annotated[str, StringConstraints(min_length=1, max_length=128)]
    new_password: Password


class UserOutput(StrictModel):
    id: str
    email: str
    name: str
    country: str
    created_at: datetime


class TokenOutput(StrictModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
