import logging
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.comments.schemas import (
    CommentCreate,
    CommentUpdate,
    CommentResponse,
)
from app.core.dependencies import get_current_user
from app.db.database import database
from app.worker.tasks import send_notification

router = APIRouter(prefix="/api/comments", tags=["Comments"])

logger = logging.getLogger(__name__)


@router.post(
    "/",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    comment: CommentCreate,
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])

    if bool(comment.task_id) == bool(comment.project_id):
        raise HTTPException(
            status_code=400,
            detail="Provide either a task ID or a project ID, not both",
        )

    task = None

    if comment.task_id:
        if not ObjectId.is_valid(comment.task_id):
            raise HTTPException(status_code=404, detail="Task not found")

        task = await database["tasks"].find_one(
            {"_id": ObjectId(comment.task_id)}
        )

        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")

        project_id = task["project_id"]

    else:
        if not ObjectId.is_valid(comment.project_id):
            raise HTTPException(status_code=404, detail="Project not found")

        project_id = comment.project_id

    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=404, detail="Project not found")

    project = await database["projects"].find_one(
        {
            "_id": ObjectId(project_id),
            "$or": [
                {"owner_id": user_id},
                {"team_members": user_id},
            ],
        }
    )

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    comment_data = {
        "text": comment.text,
        "author_id": user_id,
        "created_at": datetime.now(timezone.utc),
        "task_id": comment.task_id,
        "project_id": project_id,
    }

    result = await database["comments"].insert_one(comment_data)

    recipient_id = (
        task.get("assignee_id")
        if task
        else project.get("owner_id")
    )

    if recipient_id and recipient_id != user_id:
        send_notification.delay(
            recipient_id,
            f"New comment on your project or task: {comment.text}",
        )

    logger.info("Comment created by user %s", user_id)

    return {"id": str(result.inserted_id), **comment_data}


@router.get("/", response_model=list[CommentResponse])
async def list_comments(
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

    comments = await database["comments"].find(
        {"project_id": {"$in": project_ids}}
    ).sort("created_at", -1).to_list(length=100)

    return [
        {
            "id": str(comment["_id"]),
            "text": comment["text"],
            "author_id": comment["author_id"],
            "created_at": comment["created_at"],
            "task_id": comment.get("task_id"),
            "project_id": comment.get("project_id"),
        }
        for comment in comments
    ]


@router.get("/{comment_id}", response_model=CommentResponse)
async def get_comment(
    comment_id: str,
    current_user: dict = Depends(get_current_user),
):
    if not ObjectId.is_valid(comment_id):
        raise HTTPException(status_code=404, detail="Comment not found")

    user_id = str(current_user["_id"])

    comment = await database["comments"].find_one(
        {"_id": ObjectId(comment_id)}
    )

    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")

    project_id = comment.get("project_id")

    if not project_id and comment.get("task_id"):
        if not ObjectId.is_valid(comment["task_id"]):
            raise HTTPException(status_code=404, detail="Comment not found")

        task = await database["tasks"].find_one(
            {"_id": ObjectId(comment["task_id"])}
        )

        if task is None:
            raise HTTPException(status_code=404, detail="Comment not found")

        project_id = task["project_id"]

    if not project_id or not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=404, detail="Comment not found")

    project = await database["projects"].find_one(
        {
            "_id": ObjectId(project_id),
            "$or": [
                {"owner_id": user_id},
                {"team_members": user_id},
            ],
        }
    )

    if project is None:
        raise HTTPException(status_code=404, detail="Comment not found")

    return {
        "id": str(comment["_id"]),
        "text": comment["text"],
        "author_id": comment["author_id"],
        "created_at": comment["created_at"],
        "task_id": comment.get("task_id"),
        "project_id": project_id,
    }


@router.patch("/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: str,
    comment_update: CommentUpdate,
    current_user: dict = Depends(get_current_user),
):
    if not ObjectId.is_valid(comment_id):
        raise HTTPException(status_code=404, detail="Comment not found")

    user_id = str(current_user["_id"])

    result = await database["comments"].update_one(
        {
            "_id": ObjectId(comment_id),
            "author_id": user_id,
        },
        {"$set": {"text": comment_update.text}},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Comment not found")

    comment = await database["comments"].find_one(
        {"_id": ObjectId(comment_id)}
    )

    logger.info("Comment updated by user %s", user_id)

    return {
        "id": str(comment["_id"]),
        "text": comment["text"],
        "author_id": comment["author_id"],
        "created_at": comment["created_at"],
        "task_id": comment.get("task_id"),
        "project_id": comment.get("project_id"),
    }


@router.delete(
    "/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_comment(
    comment_id: str,
    current_user: dict = Depends(get_current_user),
):
    if not ObjectId.is_valid(comment_id):
        raise HTTPException(status_code=404, detail="Comment not found")

    user_id = str(current_user["_id"])

    result = await database["comments"].delete_one(
        {
            "_id": ObjectId(comment_id),
            "author_id": user_id,
        }
    )

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Comment not found")

    logger.info("Comment deleted by user %s", user_id)
