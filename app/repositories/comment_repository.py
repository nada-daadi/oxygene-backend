from datetime import datetime, timezone, timedelta
from typing import Any
from urllib.parse import urlparse, urlunparse

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING

from app.core.database import database

comments_collection = database["comments"]

PAGE_SIZE_DEFAULT = 20
PAGE_SIZE_MAX = 50


# ─── URL Normalization ────────────────────────────────────────────────────────

def normalize_url(raw_url: str) -> str:
    """
    Normalize a scraped article URL for consistent storage:
    - Strip leading/trailing whitespace
    - Strip trailing slash
    - Lowercase scheme + host (preserve path case)
    - Strip 'www.' prefix from hostname
    """
    raw_url = raw_url.strip().rstrip("/")
    try:
        parsed = urlparse(raw_url)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        normalized = urlunparse((scheme, netloc, parsed.path, parsed.params, parsed.query, ""))
        return normalized
    except Exception:
        return raw_url


# ─── Indexes ──────────────────────────────────────────────────────────────────

async def create_comment_indexes() -> None:
    await comments_collection.create_index(
        [("article_url", ASCENDING)],
        name="comments_article_url_index",
    )
    await comments_collection.create_index(
        [("user_id", ASCENDING)],
        name="comments_user_id_index",
    )
    await comments_collection.create_index(
        [("created_at", DESCENDING)],
        name="comments_created_at_index",
    )
    # Compound index for spam check
    await comments_collection.create_index(
        [("user_id", ASCENDING), ("article_url", ASCENDING), ("created_at", DESCENDING)],
        name="comments_spam_check_index",
    )


# ─── Serializer ───────────────────────────────────────────────────────────────

def serialize_comment(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(doc["_id"]),
        "user_id": doc["user_id"],
        "username": doc["username"],
        "article_url": doc["article_url"],
        "article_title": doc.get("article_title", ""),
        "content": doc["content"],
        "created_at": doc["created_at"],
        "updated_at": doc.get("updated_at"),
    }


# ─── CRUD ─────────────────────────────────────────────────────────────────────

async def create_comment(
    user_id: str,
    username: str,
    article_url: str,
    article_title: str,
    content: str,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user_id,
        "username": username,
        "article_url": normalize_url(article_url),
        "article_title": article_title,
        "content": content,
        "created_at": now,
        "updated_at": None,
    }
    result = await comments_collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def get_comments_by_article(
    article_url: str,
    page: int = 1,
    page_size: int = PAGE_SIZE_DEFAULT,
) -> list[dict[str, Any]]:
    page_size = min(page_size, PAGE_SIZE_MAX)
    skip = (page - 1) * page_size
    cursor = (
        comments_collection.find({"article_url": normalize_url(article_url)})
        .sort("created_at", DESCENDING)
        .skip(skip)
        .limit(page_size)
    )
    return await cursor.to_list(length=page_size)


async def count_comments_by_article(article_url: str) -> int:
    return await comments_collection.count_documents(
        {"article_url": normalize_url(article_url)}
    )


async def get_comment_by_id(comment_id: str) -> dict[str, Any] | None:
    if not ObjectId.is_valid(comment_id):
        return None
    return await comments_collection.find_one({"_id": ObjectId(comment_id)})


async def update_comment(comment_id: str, content: str) -> dict[str, Any] | None:
    if not ObjectId.is_valid(comment_id):
        return None
    now = datetime.now(timezone.utc)
    result = await comments_collection.find_one_and_update(
        {"_id": ObjectId(comment_id)},
        {"$set": {"content": content, "updated_at": now}},
        return_document=True,
    )
    return result


async def delete_comment(comment_id: str) -> bool:
    if not ObjectId.is_valid(comment_id):
        return False
    result = await comments_collection.delete_one({"_id": ObjectId(comment_id)})
    return result.deleted_count == 1


async def delete_comments_by_user_id(user_id: str) -> int:
    """Cascade delete when user account is removed."""
    result = await comments_collection.delete_many({"user_id": user_id})
    return result.deleted_count


# ─── Spam Check ───────────────────────────────────────────────────────────────

async def count_recent_comments_by_user(
    user_id: str,
    article_url: str,
    within_minutes: int = 60,
) -> int:
    since = datetime.now(timezone.utc) - timedelta(minutes=within_minutes)
    return await comments_collection.count_documents(
        {
            "user_id": user_id,
            "article_url": normalize_url(article_url),
            "created_at": {"$gte": since},
        }
    )
