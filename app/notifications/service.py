
from datetime import datetime, timezone

from app.db.database import database


async def create_notification(user_id: str, text: str):
    notification = {
        "text": text,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
        "mark_read": False,
    }

    result = await database["notifications"].insert_one(notification)

    notification["id"] = str(result.inserted_id)

    return notification
