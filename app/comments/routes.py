import logging

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user
from app.db.database import database
from app.comments.schemas import (
    CommentCreate,
    CommentUpdate,
    CommentResponse,
)


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

    if not comment.task_id and not comment.project_id:
        raise HTTPException(
            status_code=400,
            detail="Provide either a task ID or a project ID",
        )

    if comment.task_id and comment.project_id:
        raise HTTPException(
            status_code=400,
            detail="Provide either a task ID or a project ID, not both",
        )

    if comment.task_id:
        if not ObjectId.is_valid(comment.task_id):
            raise HTTPException(
                status_code=404,
                detail="Task not found",
            )

        task = await database["tasks"].find_one(
            {"_id": ObjectId(comment.task_id)}
        )

        if task is None:
            raise HTTPException(
                status_code=404,
                detail="Task not found",
            )

        project = await database["projects"].find_one(
            {"_id": ObjectId(task["project_id"])}
        )

    else:
        if not ObjectId.is_valid(comment.project_id):
            raise HTTPException(
                status_code=404,
                detail="Project not found",
            )

        project = await database["projects"].find_one(
            {"_id": ObjectId(comment.project_id)}
        )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    if (
        project["owner_id"] != user_id
        and user_id not in project.get("team_members", [])
    ):
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    comment_data = {
        "text": comment.text,
        "author_id": user_id,
        "created_at": datetime.now(timezone.utc),
        "task_id": comment.task_id,
        "project_id": comment.project_id,
    }

    result = await database["comments"].insert_one(comment_data)

    logger.info("Comment created by user %s", user_id)

    return {
        "id": str(result.inserted_id),
        **comment_data,
    }


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

    tasks = await database["tasks"].find(
        {"project_id": {"$in": project_ids}}
    ).to_list(length=100)

    task_ids = [str(task["_id"]) for task in tasks]

    comments = await database["comments"].find(
        {
            "$or": [
                {"project_id": {"$in": project_ids}},
                {"task_id": {"$in": task_ids}},
            ]
        }
    ).to_list(length=100)

    comment_list = []

    for comment in comments:
        comment_list.append({
            "id": str(comment["_id"]),
            "text": comment["text"],
            "author_id": comment["author_id"],
            "created_at": comment["created_at"],
            "task_id": comment.get("task_id"),
            "project_id": comment.get("project_id"),
        })

    return comment_list


@router.get("/{comment_id}", response_model=CommentResponse)
async def get_comment(
    comment_id: str,
    current_user: dict = Depends(get_current_user),
):
    if not ObjectId.is_valid(comment_id):
        raise HTTPException(
            status_code=404,
            detail="Comment not found",
        )

    user_id = str(current_user["_id"])

    comment = await database["comments"].find_one(
        {"_id": ObjectId(comment_id)}
    )

    if comment is None:
        raise HTTPException(
            status_code=404,
            detail="Comment not found",
        )

    if comment.get("project_id"):
        project_id = comment["project_id"]
    else:
        task = await database["tasks"].find_one(
            {"_id": ObjectId(comment["task_id"])}
        )

        if task is None:
            raise HTTPException(
                status_code=404,
                detail="Comment not found",
            )

        project_id = task["project_id"]

    project = await database["projects"].find_one(
        {"_id": ObjectId(project_id)}
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Comment not found",
        )

    if (
        project["owner_id"] != user_id
        and user_id not in project.get("team_members", [])
    ):
        raise HTTPException(
            status_code=404,
            detail="Comment not found",
        )

    return {
        "id": str(comment["_id"]),
        "text": comment["text"],
        "author_id": comment["author_id"],
        "created_at": comment["created_at"],
        "task_id": comment.get("task_id"),
        "project_id": comment.get("project_id"),
    }


@router.patch("/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: str,
    comment_update: CommentUpdate,
    current_user: dict = Depends(get_current_user),
):
    if not ObjectId.is_valid(comment_id):
        raise HTTPException(
            status_code=404,
            detail="Comment not found",
        )

    user_id = str(current_user["_id"])

    comment = await database["comments"].find_one(
        {
            "_id": ObjectId(comment_id),
            "author_id": user_id,
        }
    )

    if comment is None:
        raise HTTPException(
            status_code=404,
            detail="Comment not found",
        )

    await database["comments"].update_one(
        {"_id": ObjectId(comment_id)},
        {"$set": {"text": comment_update.text}},
    )

    updated_comment = await database["comments"].find_one(
        {"_id": ObjectId(comment_id)}
    )

    logger.info("Comment updated by user %s", user_id)

    return {
        "id": str(updated_comment["_id"]),
        "text": updated_comment["text"],
        "author_id": updated_comment["author_id"],
        "created_at": updated_comment["created_at"],
        "task_id": updated_comment.get("task_id"),
        "project_id": updated_comment.get("project_id"),
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
        raise HTTPException(
            status_code=404,
            detail="Comment not found",
        )

    user_id = str(current_user["_id"])

    result = await database["comments"].delete_one(
        {
            "_id": ObjectId(comment_id),
            "author_id": user_id,
        }
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Comment not found",
        )

    logger.info("Comment deleted by user %s", user_id)