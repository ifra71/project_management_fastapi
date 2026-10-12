from fastapi import FastAPI

from app.accounts.routes import router as accounts_router
from app.core.config import settings
from app.db.database import lifespan

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A project management app ",
    lifespan=lifespan,
)

app.include_router(accounts_router)


@app.get("/")
async def home():
    return {"message": "API is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
