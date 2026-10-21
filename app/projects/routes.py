import logging
from datetime import date

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user, require_project_manager
from app.db.database import database
from app.projects.schemas import ProjectCreate, ProjectResponse, ProjectUpdate
from app.timeline.service import create_timeline_event
from app.worker.tasks import send_notification

router = APIRouter(prefix="/api/projects", tags=["Projects"])

logger = logging.getLogger(__name__)


@router.post(
    "/",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    project: ProjectCreate,
    current_user: dict = Depends(require_project_manager),
):
    user_id = str(current_user["_id"])

    if project.end_date < project.start_date:
        raise HTTPException(
            status_code=400,
            detail="End date cannot be before start date",
        )

    for member_id in project.team_members:
        if not ObjectId.is_valid(member_id):
            raise HTTPException(
                status_code=400,
                detail="Invalid team member ID",
            )

        member = await database["users"].find_one(
            {"_id": ObjectId(member_id)}
        )

        if member is None:
            raise HTTPException(
                status_code=404,
                detail="Team member not found",
            )

    project_data = {
        "title": project.title,
        "description": project.description,
        "start_date": project.start_date.isoformat(),
        "end_date": project.end_date.isoformat(),
        "team_members": project.team_members,
        "owner_id": user_id,
    }

    result = await database["projects"].insert_one(project_data)
    project_id = str(result.inserted_id)

    await create_timeline_event(
        event_type="project_created",
        project_id=project_id,
        user_id=user_id,
    )

    for member_id in set(project.team_members):
        if member_id != user_id:
            send_notification.delay(
                member_id,
                f"You have been added to the project: {project.title}",
            )

    logger.info("Project created by user %s", user_id)

    return {
        "id": project_id,
        **project_data,
    }


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
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

    return [
        {
            "id": str(project["_id"]),
            "title": project["title"],
            "description": project.get("description"),
            "start_date": project["start_date"],
            "end_date": project["end_date"],
            "team_members": project.get("team_members", []),
            "owner_id": project["owner_id"],
        }
        for project in projects
    ]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    user_id = str(current_user["_id"])

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
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    return {
        "id": str(project["_id"]),
        "title": project["title"],
        "description": project.get("description"),
        "start_date": project["start_date"],
        "end_date": project["end_date"],
        "team_members": project.get("team_members", []),
        "owner_id": project["owner_id"],
    }


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    current_user: dict = Depends(require_project_manager),
):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    user_id = str(current_user["_id"])

    project = await database["projects"].find_one(
        {
            "_id": ObjectId(project_id),
            "owner_id": user_id,
        }
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    update_data = project_update.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update",
        )

    for field in ["start_date", "end_date"]:
        if field in update_data:
            if update_data[field] is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"{field} cannot be null",
                )

            update_data[field] = update_data[field].isoformat()

    if "team_members" in update_data:
        if update_data["team_members"] is None:
            raise HTTPException(
                status_code=400,
                detail="Team members cannot be null",
            )

        for member_id in update_data["team_members"]:
            if not ObjectId.is_valid(member_id):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid team member ID",
                )

            member = await database["users"].find_one(
                {"_id": ObjectId(member_id)}
            )

            if member is None:
                raise HTTPException(
                    status_code=404,
                    detail="Team member not found",
                )

    start_date = date.fromisoformat(
        update_data.get("start_date", project["start_date"])
    )
    end_date = date.fromisoformat(
        update_data.get("end_date", project["end_date"])
    )

    if end_date < start_date:
        raise HTTPException(
            status_code=400,
            detail="End date cannot be before start date",
        )

    old_members = set(project.get("team_members", []))
    new_members = set(update_data.get("team_members", old_members))

    result = await database["projects"].update_one(
        {"_id": ObjectId(project_id), "owner_id": user_id},
        {"$set": update_data},
    )

    if result.modified_count > 0:
        await create_timeline_event(
            event_type="project_updated",
            project_id=project_id,
            user_id=user_id,
        )

    for member_id in new_members - old_members:
        if member_id != user_id:
            send_notification.delay(
                member_id,
                f"You have been added to the project: {project['title']}",
            )

    updated_project = await database["projects"].find_one(
        {"_id": ObjectId(project_id)}
    )

    logger.info("Project updated by user %s", user_id)

    return {
        "id": str(updated_project["_id"]),
        "title": updated_project["title"],
        "description": updated_project.get("description"),
        "start_date": updated_project["start_date"],
        "end_date": updated_project["end_date"],
        "team_members": updated_project.get("team_members", []),
        "owner_id": updated_project["owner_id"],
    }


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project(
    project_id: str,
    current_user: dict = Depends(require_project_manager),
):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    user_id = str(current_user["_id"])

    project = await database["projects"].find_one(
        {
            "_id": ObjectId(project_id),
            "owner_id": user_id,
        }
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    result = await database["projects"].delete_one(
        {
            "_id": ObjectId(project_id),
            "owner_id": user_id,
        }
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    await create_timeline_event(
        event_type="project_deleted",
        project_id=project_id,
        user_id=user_id,
    )

    logger.info("Project deleted by user %s", user_id)
