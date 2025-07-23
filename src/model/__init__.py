from beanie import init_beanie
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from .key_value import KeyValue
from .message import Message

client: AsyncDatabase | None = None


async def init_mongodb(*, user: str, password: str, host: str, port: int, db_name: str):
    global client
    client = AsyncMongoClient(
        f"mongodb://{user}:{password}@{host}:{port}"
    ).get_database(db_name)
    if client is None:
        raise ValueError("Failed to connect to MongoDB")

    await init_beanie(database=client, document_models=[KeyValue, Message])

    return client


def get_client() -> AsyncDatabase:
    if client is None:
        raise ValueError("MongoDB client not initialized")
    return client
