
from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    text: str
    user_id: str
    created_at: datetime
    mark_read: bool = False


class NotificationUpdate(BaseModel):
    mark_read: bool
