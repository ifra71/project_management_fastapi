
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


ProfileRole = Literal["manager", "qa", "developer", "designer", "other"]


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    name: str = Field(min_length=2, max_length=100)
    role: ProfileRole = "other"
    contact_number: str = Field(default="", max_length=20)


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)
