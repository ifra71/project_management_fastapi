import logging

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user
from app.db.database import database
from app.documents.schemas import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
)


router = APIRouter(prefix="/api/documents", tags=["Documents"])

logger = logging.getLogger(__name__)


@router.post(
    "/",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    document: DocumentCreate,
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])

    if not ObjectId.is_valid(document.project_id):
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    project = await database["projects"].find_one(
        {
            "_id": ObjectId(document.project_id),
            "$or": [
                {"owner_id": user_id},
                {"team_members": user_id},
            ],
        }
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    document_data = {
        "name": document.name,
        "description": document.description,
        "file_url": None,
        "version": 1,
        "project_id": document.project_id,
        "uploaded_by": user_id,
    }

    result = await database["documents"].insert_one(document_data)

    logger.info("Document created by user %s", user_id)

    return {
        "id": str(result.inserted_id),
        **document_data,
    }


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])

    projects = await database["projects"].find(
        {
            "$or": [
                {"owner_id": user_id},
                {"team_members": user_id},
            ]
        }
    ).to_list(length=100)

    project_ids = [str(project["_id"]) for project in projects]

    documents = await database["documents"].find(
        {"project_id": {"$in": project_ids}}
    ).to_list(length=100)

    document_list = []

    for document in documents:
        document_list.append({
            "id": str(document["_id"]),
            "name": document["name"],
            "description": document["description"],
            "file_url": document.get("file_url"),
            "version": document.get("version", 1),
            "project_id": document["project_id"],
            "uploaded_by": document["uploaded_by"],
        })

    return document_list


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    if not ObjectId.is_valid(document_id):
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    user_id = str(current_user["_id"])

    document = await database["documents"].find_one(
        {"_id": ObjectId(document_id)}
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    project = await database["projects"].find_one(
        {
            "_id": ObjectId(document["project_id"]),
            "$or": [
                {"owner_id": user_id},
                {"team_members": user_id},
            ],
        }
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    return {
        "id": str(document["_id"]),
        "name": document["name"],
        "description": document["description"],
        "file_url": document.get("file_url"),
        "version": document.get("version", 1),
        "project_id": document["project_id"],
        "uploaded_by": document["uploaded_by"],
    }


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    document_update: DocumentUpdate,
    current_user: dict = Depends(get_current_user),
):
    if not ObjectId.is_valid(document_id):
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    user_id = str(current_user["_id"])

    document = await database["documents"].find_one(
        {
            "_id": ObjectId(document_id),
            "uploaded_by": user_id,
        }
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    update_data = document_update.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update",
        )

    for field, value in update_data.items():
        if value is None:
            raise HTTPException(
                status_code=400,
                detail=f"{field} cannot be null",
            )

    await database["documents"].update_one(
        {
            "_id": ObjectId(document_id),
            "uploaded_by": user_id,
        },
        {"$set": update_data},
    )

    updated_document = await database["documents"].find_one(
        {"_id": ObjectId(document_id)}
    )

    logger.info("Document updated by user %s", user_id)

    return {
        "id": str(updated_document["_id"]),
        "name": updated_document["name"],
        "description": updated_document["description"],
        "file_url": updated_document.get("file_url"),
        "version": updated_document.get("version", 1),
        "project_id": updated_document["project_id"],
        "uploaded_by": updated_document["uploaded_by"],
    }


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    if not ObjectId.is_valid(document_id):
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    user_id = str(current_user["_id"])

    result = await database["documents"].delete_one(
        {
            "_id": ObjectId(document_id),
            "uploaded_by": user_id,
        }
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    logger.info("Document deleted by user %s", user_id)