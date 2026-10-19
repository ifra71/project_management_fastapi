from typing import Literal

from pydantic import BaseModel


ProfileRole = Literal[
    "manager",
    "qa",
    "developer",
    "designer",
    "other",
]


class ProfileCreate(BaseModel):
    role: ProfileRole = "other"
    contact_number: str = ""
    profile_picture: str | None = None


class ProfileUpdate(BaseModel):
    role: ProfileRole | None = None
    contact_number: str | None = None
    profile_picture: str | None = None


class ProfileResponse(BaseModel):
    id: str
    user_id: str
    role: ProfileRole
    contact_number: str = ""
    profile_picture: str | None = None
