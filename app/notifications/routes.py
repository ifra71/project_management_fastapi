import logging

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user
from app.db.database import database
from app.notifications.schemas import (
    NotificationResponse,
    NotificationUpdate,
)

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

logger = logging.getLogger(__name__)


@router.get("/", response_model=list[NotificationResponse])
async def list_notifications(
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])

    notifications = await database["notifications"].find(
        {"user_id": user_id}
    ).sort("created_at", -1).to_list(length=100)

    return [
        {
            "id": str(notification["_id"]),
            "text": notification["text"],
            "user_id": notification["user_id"],
            "created_at": notification["created_at"],
            "mark_read": notification.get("mark_read", False),
        }
        for notification in notifications
    ]


@router.patch("/{notification_id}", response_model=NotificationResponse)
async def update_notification(
    notification_id: str,
    notification_update: NotificationUpdate,
    current_user: dict = Depends(get_current_user),
):
    if not ObjectId.is_valid(notification_id):
        raise HTTPException(
            status_code=404,
            detail="Notification not found",
        )

    user_id = str(current_user["_id"])

    result = await database["notifications"].update_one(
        {
            "_id": ObjectId(notification_id),
            "user_id": user_id,
        },
        {
            "$set": {
                "mark_read": notification_update.mark_read,
            }
        },
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Notification not found",
        )

    notification = await database["notifications"].find_one(
        {
            "_id": ObjectId(notification_id),
            "user_id": user_id,
        }
    )

    logger.info("Notification updated for user %s", user_id)

    return {
        "id": str(notification["_id"]),
        "text": notification["text"],
        "user_id": notification["user_id"],
        "created_at": notification["created_at"],
        "mark_read": notification.get("mark_read", False),
    }


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
):
    if not ObjectId.is_valid(notification_id):
        raise HTTPException(
            status_code=404,
            detail="Notification not found",
        )

    user_id = str(current_user["_id"])

    result = await database["notifications"].delete_one(
        {
            "_id": ObjectId(notification_id),
            "user_id": user_id,
        }
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Notification not found",
        )

    logger.info("Notification deleted for user %s", user_id)
