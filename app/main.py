from fastapi import FastAPI

from app.accounts.routes import router as accounts_router
from app.projects.routes import router as projects_router
from app.tasks.routes import router as tasks_router
from app.documents.routes import router as documents_router
from app.comments.routes import router as comments_router
from app.notifications.routes import router as notifications_router
from app.timeline.routes import router as timeline_router
from app.core.config import settings
from app.db.database import lifespan
from app.profiles.routes import router as profiles_router

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A project management app",
    lifespan=lifespan,
)


app.include_router(accounts_router)
app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(documents_router)
app.include_router(comments_router)
app.include_router(notifications_router)
app.include_router(profiles_router)
app.include_router(timeline_router)


@app.get("/")
async def home():
    return {"message": "API is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
