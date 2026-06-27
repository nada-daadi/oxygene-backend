from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING

from app.core.database import database


records_collection = database["records"]


async def create_record_indexes() -> None:
    await records_collection.create_index(
        [("user_id", ASCENDING)],
        name="records_user_id_index",
    )
    await records_collection.create_index(
        [("created_at", DESCENDING)],
        name="records_created_at_index",
    )


def serialize_record(record: dict[str, Any]) -> dict[str, Any]:
    created_at = record["created_at"]
    if created_at and created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    return {
        "id": str(record["_id"]),
        "user_id": str(record["user_id"]),
        "user_name": record["user_name"],
        "source": record["source"],
        "file_url": record["file_url"],
        "cloudinary_public_id": record["cloudinary_public_id"],
        "resource_type": record["resource_type"],
        "format": record["format"],
        "original_filename": record.get("original_filename"),
        "duration_seconds": record.get("duration_seconds"),
        "created_at": created_at,
    }


async def create_record(
    user_id: str,
    user_name: str,
    source: str,
    file_url: str,
    cloudinary_public_id: str,
    resource_type: str,
    format: str,
    original_filename: str | None = None,
    duration_seconds: float | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    record_document = {
        "user_id": ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id,
        "user_name": user_name,
        "source": source,
        "file_url": file_url,
        "cloudinary_public_id": cloudinary_public_id,
        "resource_type": resource_type,
        "format": format,
        "original_filename": original_filename,
        "duration_seconds": duration_seconds,
        "created_at": now,
    }
    result = await records_collection.insert_one(record_document)
    record_document["_id"] = result.inserted_id
    return record_document


async def list_records(skip: int = 0, limit: int = 50) -> list[dict[str, Any]]:
    cursor = records_collection.find().sort("created_at", DESCENDING).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)


async def count_records() -> int:
    return await records_collection.count_documents({})


async def list_records_by_user(user_id: str, skip: int = 0, limit: int = 50) -> list[dict[str, Any]]:
    query_user_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
    cursor = records_collection.find({"user_id": query_user_id}).sort("created_at", DESCENDING).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)

async def count_records_by_user(user_id: str) -> int:
    query_user_id = ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id
    return await records_collection.count_documents({"user_id": query_user_id})
