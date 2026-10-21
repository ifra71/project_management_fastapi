from typing import Literal

from pydantic import BaseModel, Field, field_validator


ProfileRole = Literal[
    "manager",
    "qa",
    "developer",
    "designer",
    "other",
]


class ProfileCreate(BaseModel):
    role: ProfileRole = "other"
    contact_number: str = Field(default="", max_length=20)
    profile_picture: str | None = Field(default=None, max_length=500)

    @field_validator("contact_number")
    @classmethod
    def validate_contact_number(cls, value):
        if value and not any(char.isdigit() for char in value):
            raise ValueError("Contact number must contain at least one digit")

        return value

    @field_validator("profile_picture")
    @classmethod
    def validate_profile_picture(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Profile picture cannot contain only whitespace")

        return value


class ProfileUpdate(BaseModel):
    role: ProfileRole | None = None
    contact_number: str | None = Field(default=None, max_length=20)
    profile_picture: str | None = Field(default=None, max_length=500)

    @field_validator("contact_number")
    @classmethod
    def validate_contact_number(cls, value):
        if value and not any(char.isdigit() for char in value):
            raise ValueError("Contact number must contain at least one digit")

        return value

    @field_validator("profile_picture")
    @classmethod
    def validate_profile_picture(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Profile picture cannot contain only whitespace")

        return value


class ProfileResponse(BaseModel):
    id: str
    user_id: str
    role: ProfileRole
    contact_number: str = Field(default="", max_length=20)
    profile_picture: str | None = Field(default=None, max_length=500)
