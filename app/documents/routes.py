import logging
from pathlib import Path

from bson import ObjectId
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse

from app.core.dependencies import get_current_user
from app.db.database import database
from app.documents.schemas import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
)
from app.documents.service import save_document_file
from app.timeline.service import create_timeline_event
from app.worker.tasks import send_notification

router = APIRouter(prefix="/api/documents", tags=["Documents"])

logger = logging.getLogger(__name__)


async def get_accessible_document(document_id: str, user_id: str):
    if not ObjectId.is_valid(document_id):
        raise HTTPException(status_code=404, detail="Document not found")

    document = await database["documents"].find_one(
        {"_id": ObjectId(document_id)}
    )

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

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
        raise HTTPException(status_code=404, detail="Document not found")

    return document


def notify_project_members(project: dict, uploader_id: str, message: str):
    recipients = set(project.get("team_members", []))
    owner_id = project.get("owner_id")

    if owner_id:
        recipients.add(owner_id)

    for recipient_id in recipients:
        if recipient_id != uploader_id:
            send_notification.delay(recipient_id, message)


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
        raise HTTPException(status_code=404, detail="Project not found")

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
        raise HTTPException(status_code=404, detail="Project not found")

    document_data = {
        "name": document.name,
        "description": document.description,
        "file_url": None,
        "version": 0,
        "project_id": document.project_id,
        "uploaded_by": user_id,
    }

    result = await database["documents"].insert_one(document_data)

    await create_timeline_event(
        event_type="document_created",
        project_id=document.project_id,
        user_id=user_id,
    )

    notify_project_members(
        project,
        user_id,
        f"A new document was created: {document.name}",
    )

    logger.info("Document created by user %s", user_id)

    return {"id": str(result.inserted_id), **document_data}


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

    return [
        {
            "id": str(document["_id"]),
            "name": document["name"],
            "description": document["description"],
            "file_url": document.get("file_url"),
            "version": document.get("version", 0),
            "project_id": document["project_id"],
            "uploaded_by": document["uploaded_by"],
        }
        for document in documents
    ]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    document = await get_accessible_document(
        document_id,
        str(current_user["_id"]),
    )

    return {
        "id": str(document["_id"]),
        "name": document["name"],
        "description": document["description"],
        "file_url": document.get("file_url"),
        "version": document.get("version", 0),
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
        raise HTTPException(status_code=404, detail="Document not found")

    user_id = str(current_user["_id"])

    document = await database["documents"].find_one(
        {
            "_id": ObjectId(document_id),
            "uploaded_by": user_id,
        }
    )

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

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

    await create_timeline_event(
        event_type="document_updated",
        project_id=document["project_id"],
        user_id=user_id,
    )

    project = await database["projects"].find_one(
        {"_id": ObjectId(document["project_id"])}
    )

    if project:
        notify_project_members(
            project,
            user_id,
            f"Document updated: {updated_document['name']}",
        )

    logger.info("Document updated by user %s", user_id)

    return {
        "id": str(updated_document["_id"]),
        "name": updated_document["name"],
        "description": updated_document["description"],
        "file_url": updated_document.get("file_url"),
        "version": updated_document.get("version", 0),
        "project_id": updated_document["project_id"],
        "uploaded_by": updated_document["uploaded_by"],
    }


@router.post("/{document_id}/upload")
async def upload_document_file(
    document_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])

    document = await get_accessible_document(document_id, user_id)
    file_data = await save_document_file(file)
    new_version = document.get("version", 0) + 1

    version_data = {
        "document_id": document_id,
        "version": new_version,
        "original_name": file_data["original_name"],
        "stored_name": file_data["stored_name"],
        "file_path": file_data["file_path"],
        "size": file_data["size"],
        "uploaded_by": user_id,
    }

    try:
        await database["document_versions"].insert_one(version_data)

        await database["documents"].update_one(
            {"_id": ObjectId(document_id)},
            {
                "$set": {
                    "file_url": file_data["file_path"],
                    "version": new_version,
                }
            },
        )
    except Exception:
        Path(file_data["file_path"]).unlink(missing_ok=True)
        await database["document_versions"].delete_one(
            {
                "document_id": document_id,
                "version": new_version,
            }
        )
        raise

    await create_timeline_event(
        event_type="document_uploaded",
        project_id=document["project_id"],
        user_id=user_id,
    )

    project = await database["projects"].find_one(
        {"_id": ObjectId(document["project_id"])}
    )

    if project:
        notify_project_members(
            project,
            user_id,
            f"A new version of document '{document['name']}' was uploaded.",
        )

    logger.info(
        "Document %s uploaded by user %s",
        document_id,
        user_id,
    )

    return {
        "message": "Document uploaded successfully",
        "document_id": document_id,
        "filename": file_data["original_name"],
        "version": new_version,
        "size": file_data["size"],
    }


@router.get("/{document_id}/versions")
async def list_document_versions(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    await get_accessible_document(
        document_id,
        str(current_user["_id"]),
    )

    versions = await database["document_versions"].find(
        {"document_id": document_id}
    ).sort("version", -1).to_list(length=100)

    return [
        {
            "version": version["version"],
            "filename": version["original_name"],
            "size": version["size"],
            "uploaded_by": version["uploaded_by"],
        }
        for version in versions
    ]


@router.get("/{document_id}/versions/{version_number}/download")
async def download_document_version(
    document_id: str,
    version_number: int,
    current_user: dict = Depends(get_current_user),
):
    await get_accessible_document(
        document_id,
        str(current_user["_id"]),
    )

    version = await database["document_versions"].find_one(
        {
            "document_id": document_id,
            "version": version_number,
        }
    )

    if version is None:
        raise HTTPException(
            status_code=404,
            detail="Document version not found",
        )

    file_path = Path(version["file_path"])

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="File not found on storage",
        )

    return FileResponse(
        path=file_path,
        filename=version["original_name"],
    )


@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    document = await get_accessible_document(
        document_id,
        str(current_user["_id"]),
    )

    file_path_value = document.get("file_url")

    if not file_path_value:
        raise HTTPException(
            status_code=404,
            detail="No file uploaded for this document",
        )

    file_path = Path(file_path_value)

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="File not found on storage",
        )

    latest_version = await database["document_versions"].find_one(
        {
            "document_id": document_id,
            "version": document.get("version", 0),
        }
    )

    filename = (
        latest_version["original_name"]
        if latest_version
        else document["name"]
    )

    return FileResponse(
        path=file_path,
        filename=filename,
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    if not ObjectId.is_valid(document_id):
        raise HTTPException(status_code=404, detail="Document not found")

    user_id = str(current_user["_id"])

    document = await database["documents"].find_one(
        {
            "_id": ObjectId(document_id),
            "uploaded_by": user_id,
        }
    )

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    result = await database["documents"].delete_one(
        {
            "_id": ObjectId(document_id),
            "uploaded_by": user_id,
        }
    )

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")

    await database["document_versions"].delete_many(
        {"document_id": document_id}
    )

    await create_timeline_event(
        event_type="document_deleted",
        project_id=document["project_id"],
        user_id=user_id,
    )

    logger.info("Document deleted by user %s", user_id)
