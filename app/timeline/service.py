from datetime import datetime, timezone

from app.db.database import database


async def create_timeline_event(
    event_type: str,
    project_id: str,
    user_id: str | None = None,
):
    event = {
        "event_type": event_type,
        "time": datetime.now(timezone.utc),
        "project_id": project_id,
        "user_id": user_id,
    }

    result = await database["timeline"].insert_one(event)

    return {
        "id": str(result.inserted_id),
        **event,
    }
