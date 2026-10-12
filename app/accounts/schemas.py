from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    name: str = Field(min_length=2, max_length=100)


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str
