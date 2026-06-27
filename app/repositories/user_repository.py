from datetime import datetime, timezone
import re
from typing import Any

from bson import ObjectId
from pymongo import ASCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.core.database import database


users_collection = database["users"]


async def create_user_indexes() -> None:
    await users_collection.create_index(
        [("email", ASCENDING)],
        unique=True,
        name="users_email_unique",
    )


def serialize_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "is_active": user.get("is_active", True),
        "bio": user.get("bio"),
        "avatar_url": user.get("avatar_url"),
        "provider": user.get("provider"),
        "google_id": user.get("google_id"),
        "is_email_verified": user.get("is_email_verified", False),
        "created_at": user["created_at"],
        "updated_at": user["updated_at"],
    }


async def get_user_by_email(email: str) -> dict[str, Any] | None:
    return await users_collection.find_one({"email": email.lower()})


async def get_user_by_name(
    name: str,
    exclude_user_id: str | None = None,
) -> dict[str, Any] | None:
    query: dict[str, Any] = {
        "name": {"$regex": f"^{re.escape(name.strip())}$", "$options": "i"}
    }

    if exclude_user_id and ObjectId.is_valid(exclude_user_id):
        query["_id"] = {"$ne": ObjectId(exclude_user_id)}

    return await users_collection.find_one(query)


async def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    if not ObjectId.is_valid(user_id):
        return None

    return await users_collection.find_one({"_id": ObjectId(user_id)})


async def create_user(
    name: str,
    email: str,
    hashed_password: str | None,
    phone: str | None = None,
    sexe: str | None = None,
    adresse: str | None = None,
    provider: str | None = None,
    google_id: str | None = None,
    is_email_verified: bool = False,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    user_document = {
        "name": name.strip(),
        "email": email.lower(),
        "hashed_password": hashed_password,
        "provider": provider,
        "google_id": google_id,
        "is_email_verified": is_email_verified,
        "is_active": True,
        "bio": None,
        "avatar_url": None,
        "avatar_public_id": None,
        "phone": phone,
        "sexe": sexe,
        "adresse": adresse,
        "created_at": now,
        "updated_at": now,
    }
    result = await users_collection.insert_one(user_document)
    user_document["_id"] = result.inserted_id
    return user_document


async def update_user(user_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    if not ObjectId.is_valid(user_id):
        return None

    update_document: dict[str, Any] = {}
    if "name" in updates and updates["name"] is not None:
        update_document["name"] = updates["name"].strip()
    if "email" in updates and updates["email"] is not None:
        update_document["email"] = updates["email"].lower()
    if "bio" in updates:
        update_document["bio"] = updates["bio"]
    if "avatar_url" in updates:
        update_document["avatar_url"] = updates["avatar_url"]
    if "avatar_public_id" in updates:
        update_document["avatar_public_id"] = updates["avatar_public_id"]
    if "hashed_password" in updates and updates["hashed_password"] is not None:
        update_document["hashed_password"] = updates["hashed_password"]
    if "provider" in updates:
        update_document["provider"] = updates["provider"]
    if "google_id" in updates:
        update_document["google_id"] = updates["google_id"]
    if "is_email_verified" in updates:
        update_document["is_email_verified"] = updates["is_email_verified"]

    if not update_document:
        return await get_user_by_id(user_id)

    update_document["updated_at"] = datetime.now(timezone.utc)

    try:
        return await users_collection.find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$set": update_document},
            return_document=ReturnDocument.AFTER,
        )
    except DuplicateKeyError:
        raise


async def delete_user(user_id: str) -> bool:
    if not ObjectId.is_valid(user_id):
        return False

    result = await users_collection.delete_one({"_id": ObjectId(user_id)})
    return result.deleted_count == 1
