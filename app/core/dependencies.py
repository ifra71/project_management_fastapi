
import logging

from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import settings
from app.db.database import database

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/accounts/login")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    blacklisted_token = await database["blacklisted_tokens"].find_one(
        {"token": token}
    )

    if blacklisted_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        user_id = payload.get("sub")

        if not user_id or not ObjectId.is_valid(user_id):
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    current_user = await database["users"].find_one(
        {"_id": ObjectId(user_id)}
    )

    if current_user is None:
        raise credentials_exception

    return current_user


async def require_project_manager(
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])

    profile = await database["profiles"].find_one(
        {"user_id": user_id}
    )

    role = profile.get("role") if profile else None

    logger.warning(
        "Permission check: user_id=%s, role=%s",
        user_id,
        role,
    )

    if role != "manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project managers can perform this action",
        )

    return current_user



