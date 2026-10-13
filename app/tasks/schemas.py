
from pydantic import BaseModel


class TaskCreate(BaseModel):
    title: str
    description: str
    status: str = "open"
    project_id: str
    assignee_id: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    assignee_id: str | None = None


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    status: str
    project_id: str
    assignee_id: str | None = None
