from contextlib import asynccontextmanager

from pymongo import AsyncMongoClient

from app.core.config import settings

client = AsyncMongoClient(settings.mongodb_url)
database = client[settings.database_name]


async def connect_to_mongodb():
    await client.admin.command("ping")
    await database["users"].create_index("email", unique=True)
    print("MongoDB connection successful")


async def close_mongodb_connection():
    await client.close()


@asynccontextmanager
async def lifespan(app):
    await connect_to_mongodb()
    yield
    await close_mongodb_connection()
