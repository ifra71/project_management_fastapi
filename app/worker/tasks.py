from datetime import datetime, timezone

from pymongo import MongoClient
from app.core.config import settings
from app.worker.celery_app import celery_app


@celery_app.task
def send_notification(user_id: str, message: str):
    client = MongoClient(
        settings.mongodb_url,
        serverSelectionTimeoutMS=5000,
    )

    try:
        database = client[settings.database_name]

        notification = {
            "text": message,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc),
            "mark_read": False,
        }

        result = database["notifications"].insert_one(notification)

        return {
            "id": str(result.inserted_id),
            "user_id": user_id,
            "message": message,
        }
    finally:
        client.close()
