from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from app.core.database import database


favorites_collection = database["favorites"]


async def create_favorite_indexes() -> None:
    await favorites_collection.create_index(
        [("user_id", ASCENDING), ("article_id", ASCENDING)],
        unique=True,
        name="favorites_user_article_unique",
    )
    await favorites_collection.create_index(
        [("user_id", ASCENDING)],
        name="favorites_user_id_index",
    )


def serialize_favorite(favorite: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(favorite["_id"]),
        "user_id": favorite["user_id"],
        "article_id": favorite["article_id"],
        "created_at": favorite["created_at"],
    }


async def get_user_favorites(user_id: str) -> list[dict[str, Any]]:
    cursor = favorites_collection.find({"user_id": user_id}).sort("created_at", DESCENDING)
    return await cursor.to_list(length=None)


async def get_favorite_by_article(
    user_id: str,
    article_id: str,
) -> dict[str, Any] | None:
    return await favorites_collection.find_one(
        {
            "user_id": user_id,
            "article_id": article_id.strip(),
        }
    )


async def add_favorite(user_id: str, article_id: str) -> dict[str, Any]:
    favorite_document = {
        "user_id": user_id,
        "article_id": article_id.strip(),
        "created_at": datetime.now(timezone.utc),
    }

    try:
        result = await favorites_collection.insert_one(favorite_document)
    except DuplicateKeyError:
        raise

    favorite_document["_id"] = result.inserted_id
    return favorite_document


async def remove_favorite(user_id: str, article_id: str) -> bool:
    result = await favorites_collection.delete_one(
        {
            "user_id": user_id,
            "article_id": article_id.strip(),
        }
    )
    return result.deleted_count == 1


async def delete_favorites_by_user_id(user_id: str) -> int:
    if ObjectId.is_valid(user_id):
        result = await favorites_collection.delete_many({"user_id": user_id})
        return result.deleted_count

    return 0
