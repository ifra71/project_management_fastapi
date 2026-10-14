import logging

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user
from app.db.database import database
from app.tasks.schemas import TaskCreate, TaskUpdate, TaskResponse


router = APIRouter(prefix="/api/tasks", tags=["Tasks"])

logger = logging.getLogger(__name__)


@router.post(
    "/",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    task: TaskCreate,
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])

    if not ObjectId.is_valid(task.project_id):
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    project = await database["projects"].find_one(
        {
            "_id": ObjectId(task.project_id),
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

    if task.assignee_id is not None:
        if not ObjectId.is_valid(task.assignee_id):
            raise HTTPException(
                status_code=400,
                detail="Invalid assignee ID",
            )

        member = await database["users"].find_one(
            {"_id": ObjectId(task.assignee_id)}
        )

        if member is None:
            raise HTTPException(
                status_code=404,
                detail="Assignee not found",
            )

        if (
            task.assignee_id != project["owner_id"]
            and task.assignee_id not in project.get("team_members", [])
        ):
            raise HTTPException(
                status_code=400,
                detail="Assignee must belong to the project team",
            )

    task_data = {
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "project_id": task.project_id,
        "assignee_id": task.assignee_id,
        "created_by": user_id,
    }

    result = await database["tasks"].insert_one(task_data)

    logger.info("Task created by user %s", user_id)

    return {
        "id": str(result.inserted_id),
        **task_data,
    }


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
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

    task_list = []

    for task in tasks:
        task_list.append({
            "id": str(task["_id"]),
            "title": task["title"],
            "description": task["description"],
            "status": task["status"],
            "project_id": task["project_id"],
            "assignee_id": task.get("assignee_id"),
        })

    return task_list


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    if not ObjectId.is_valid(task_id):
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    user_id = str(current_user["_id"])

    task = await database["tasks"].find_one(
        {"_id": ObjectId(task_id)}
    )

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    project = await database["projects"].find_one(
        {
            "_id": ObjectId(task["project_id"]),
            "$or": [
                {"owner_id": user_id},
                {"team_members": user_id},
            ],
        }
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    return {
        "id": str(task["_id"]),
        "title": task["title"],
        "description": task["description"],
        "status": task["status"],
        "project_id": task["project_id"],
        "assignee_id": task.get("assignee_id"),
    }


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_update: TaskUpdate,
    current_user: dict = Depends(get_current_user),
):
    if not ObjectId.is_valid(task_id):
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    user_id = str(current_user["_id"])

    task = await database["tasks"].find_one(
        {"_id": ObjectId(task_id)}
    )

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    project = await database["projects"].find_one(
        {
            "_id": ObjectId(task["project_id"]),
            "$or": [
                {"owner_id": user_id},
                {"team_members": user_id},
            ],
        }
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    update_data = task_update.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update",
        )

    if "assignee_id" in update_data:
        assignee_id = update_data["assignee_id"]

        if assignee_id is not None:
            if not ObjectId.is_valid(assignee_id):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid assignee ID",
                )

            member = await database["users"].find_one(
                {"_id": ObjectId(assignee_id)}
            )

            if member is None:
                raise HTTPException(
                    status_code=404,
                    detail="Assignee not found",
                )

            if (
                assignee_id != project["owner_id"]
                and assignee_id not in project.get("team_members", [])
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Assignee must belong to the project team",
                )

    await database["tasks"].update_one(
        {"_id": ObjectId(task_id)},
        {"$set": update_data},
    )

    updated_task = await database["tasks"].find_one(
        {"_id": ObjectId(task_id)}
    )

    logger.info("Task updated by user %s", user_id)

    return {
        "id": str(updated_task["_id"]),
        "title": updated_task["title"],
        "description": updated_task["description"],
        "status": updated_task["status"],
        "project_id": updated_task["project_id"],
        "assignee_id": updated_task.get("assignee_id"),
    }


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    if not ObjectId.is_valid(task_id):
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    user_id = str(current_user["_id"])

    task = await database["tasks"].find_one(
        {"_id": ObjectId(task_id)}
    )

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    project = await database["projects"].find_one(
        {
            "_id": ObjectId(task["project_id"]),
            "$or": [
                {"owner_id": user_id},
                {"team_members": user_id},
            ],
        }
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    await database["tasks"].delete_one(
        {"_id": ObjectId(task_id)}
    )

    logger.info("Task deleted by user %s", user_id)
