
from pydantic import BaseModel


class DocumentCreate(BaseModel):
    name: str
    description: str
    project_id: str


class DocumentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class DocumentResponse(BaseModel):
    id: str
    name: str
    description: str
    file_url: str | None = None
    version: int = 1
    project_id: str
    uploaded_by: str
