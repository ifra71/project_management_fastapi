from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.core.dependencies import get_current_user
from app.db.database import database
from app.profiles.schemas import (
    ProfileCreate,
    ProfileUpdate,
    ProfileResponse,
)

router = APIRouter(prefix="/api/profiles", tags=["Profiles"])


@router.post(
    "/",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_profile(
    profile_data: ProfileCreate,
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])

    profile = profile_data.model_dump()
    profile["user_id"] = user_id

    try:
        result = await database["profiles"].insert_one(profile)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile already exists",
        )

    return {
        "id": str(result.inserted_id),
        **profile,
    }


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])

    profile = await database["profiles"].find_one(
        {"user_id": user_id}
    )

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    profile["id"] = str(profile.pop("_id"))

    return profile


@router.patch("/me", response_model=ProfileResponse)
async def update_my_profile(
    profile_data: ProfileUpdate,
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    updates = profile_data.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )

    result = await database["profiles"].update_one(
        {"user_id": user_id},
        {"$set": updates},
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    updated_profile = await database["profiles"].find_one(
        {"user_id": user_id}
    )

    updated_profile["id"] = str(updated_profile.pop("_id"))

    return updated_profile
