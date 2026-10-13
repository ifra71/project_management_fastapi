
from datetime import date

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    title: str
    description: str
    start_date: date
    end_date: date
    team_members: list[str] = []


class ProjectUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    team_members: list[str] | None = None


class ProjectResponse(BaseModel):
    id: str
    title: str
    description: str
    start_date: date
    end_date: date
    team_members: list[str]
    owner_id: str
