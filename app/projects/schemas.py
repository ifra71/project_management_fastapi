
from datetime import date

from pydantic import BaseModel, Field, field_validator, model_validator


class ProjectCreate(BaseModel):
    title: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=5, max_length=1000)
    start_date: date
    end_date: date
    team_members: list[str] = []

    @model_validator(mode="after")
    def validate_project_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("End date cannot be earlier than start date")

        return self


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, min_length=5, max_length=1000)
    start_date: date | None = None
    end_date: date | None = None
    team_members: list[str] | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Project title cannot contain only whitespace")

        return value


class ProjectResponse(BaseModel):
    id: str
    title: str
    description: str
    start_date: date
    end_date: date
    team_members: list[str]
    owner_id: str
