from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, DESCENDING

from app.core.database import database

shares_collection = database["article_shares"]


# ---------------------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------------------


async def create_share_indexes() -> None:
    """Create MongoDB indexes for the article_shares collection."""
    # Compound index — prevents accidental duplicate tracking within the same
    # request but does NOT enforce uniqueness (users can share same article
    # multiple times on the same platform).
    await shares_collection.create_index(
        [("user_id", ASCENDING), ("article_url", ASCENDING), ("platform", ASCENDING)],
        name="shares_user_url_platform_index",
    )
    # Index for statistics aggregation grouped by article_url
    await shares_collection.create_index(
        [("article_url", ASCENDING)],
        name="shares_article_url_index",
    )
    # Index for user share history lookup
    await shares_collection.create_index(
        [("user_id", ASCENDING)],
        name="shares_user_id_index",
    )


# ---------------------------------------------------------------------------
# Serializer
# ---------------------------------------------------------------------------


def serialize_share(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(doc["_id"]),
        "user_id": doc["user_id"],
        "article_url": doc["article_url"],
        "article_title": doc.get("article_title", ""),
        "platform": doc["platform"],
        "shared_at": doc["shared_at"],
    }


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


async def create_share(
    user_id: str,
    article_url: str,
    article_title: str,
    platform: str,
) -> dict[str, Any]:
    """Insert a new share document and return it."""
    doc = {
        "user_id": user_id,
        "article_url": article_url,
        "article_title": article_title,
        "platform": platform,
        "shared_at": datetime.now(timezone.utc),
    }
    result = await shares_collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def get_share_stats(article_url: str) -> dict[str, Any]:
    """Return total share count and breakdown by platform for an article."""
    pipeline = [
        {"$match": {"article_url": article_url}},
        {
            "$group": {
                "_id": "$platform",
                "count": {"$sum": 1},
            }
        },
    ]
    cursor = shares_collection.aggregate(pipeline)
    platform_counts: dict[str, int] = {}
    total = 0
    async for doc in cursor:
        platform_counts[doc["_id"]] = doc["count"]
        total += doc["count"]

    return {
        "article_url": article_url,
        "total_shares": total,
        "shares_by_platform": platform_counts,
    }


async def get_user_shares(user_id: str) -> list[dict[str, Any]]:
    """Return all share records for a specific user (most recent first)."""
    cursor = shares_collection.find({"user_id": user_id}).sort("shared_at", DESCENDING)
    return await cursor.to_list(length=100)


async def delete_shares_by_user_id(user_id: str) -> int:
    """Remove all share records for a user (used on account deletion)."""
    result = await shares_collection.delete_many({"user_id": user_id})
    return result.deleted_count
