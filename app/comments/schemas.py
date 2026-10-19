
from datetime import datetime

from pydantic import BaseModel, Field


class CommentCreate(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    task_id: str | None = None
    project_id: str | None = None


class CommentUpdate(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class CommentResponse(BaseModel):
    id: str
    text: str
    author_id: str
    created_at: datetime
    task_id: str | None = None
    project_id: str | None = None
