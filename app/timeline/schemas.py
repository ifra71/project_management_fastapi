
from datetime import datetime

from pydantic import BaseModel


class TimelineResponse(BaseModel):
    id: str
    event_type: str
    time: datetime
    project_id: str
    user_id: str | None = None
