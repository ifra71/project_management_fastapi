from fastapi import APIRouter, HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.accounts.schemas import UserCreate, UserLogin, UserResponse
from app.core.security import hash_password, verify_password
from app.db.database import database

router = APIRouter(prefix="/api/accounts", tags=["Accounts"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(user: UserCreate):
    existing_user = await database["users"].find_one({"email": user.email})

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=" email already exists",
        )

    user_document = {
        "email": user.email,
        "name": user.name,
        "hashed_password": hash_password(user.password),
    }

    try:
        result = await database["users"].insert_one(user_document)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=" email already exists",
        )

    return UserResponse(
        id=str(result.inserted_id),
        email=user.email,
        name=user.name,
    )


@router.post("/login")
async def login_user(user: UserLogin):
    existing_user = await database["users"].find_one({"email": user.email})

    if not existing_user or not verify_password(
        user.password,
        existing_user["hashed_password"],
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return {"message": "login successful"}
