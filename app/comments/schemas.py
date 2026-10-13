
from datetime import datetime

from pydantic import BaseModel


class CommentCreate(BaseModel):
    text: str
    task_id: str | None = None
    project_id: str | None = None


class CommentUpdate(BaseModel):
    text: str


class CommentResponse(BaseModel):
    id: str
    text: str
    author_id: str
    created_at: datetime
    task_id: str | None = None
    project_id: str | None = None
