from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_current_user
from app.db.database import database
from app.timeline.schemas import TimelineResponse


router = APIRouter(prefix="/api/timeline", tags=["Timeline"])


@router.get("/{project_id}", response_model=list[TimelineResponse])
async def get_project_timeline(
    project_id: str,
    current_user: dict = Depends(get_current_user),
):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=404, detail="Project not found")

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
        raise HTTPException(status_code=404, detail="Project not found")

    events = await database["timeline"].find(
        {"project_id": project_id}
    ).sort("time", -1).to_list(length=100)

    return [
        {
            "id": str(event["_id"]),
            "event_type": event["event_type"],
            "time": event["time"],
            "project_id": event["project_id"],
            "user_id": event.get("user_id"),
        }
        for event in events
    ]
