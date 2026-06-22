from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse, urlunparse

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING, ReturnDocument

from app.core.database import database

ratings_collection = database["ratings"]

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

async def create_rating_indexes() -> None:
    await ratings_collection.create_index(
        [("article_url", ASCENDING)],
        name="ratings_article_url_index",
    )
    await ratings_collection.create_index(
        [("user_id", ASCENDING)],
        name="ratings_user_id_index",
    )
    # Compound unique index for one rating per user per article
    await ratings_collection.create_index(
        [("user_id", ASCENDING), ("article_url", ASCENDING)],
        name="ratings_user_article_unique_index",
        unique=True,
    )


# ─── Serializer ───────────────────────────────────────────────────────────────

def serialize_rating(doc: dict[str, Any]) -> dict[str, Any]:
    created_at = doc["created_at"]
    if created_at and created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
        
    updated_at = doc.get("updated_at")
    if updated_at and updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)

    return {
        "id": str(doc["_id"]),
        "user_id": doc["user_id"],
        "article_url": doc["article_url"],
        "rating": doc["rating"],
        "created_at": created_at,
        "updated_at": updated_at,
    }


# ─── CRUD ─────────────────────────────────────────────────────────────────────

async def create_or_update_rating(
    user_id: str,
    article_url: str,
    rating: int,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    normalized_url = normalize_url(article_url)
    
    doc = await ratings_collection.find_one_and_update(
        {"user_id": user_id, "article_url": normalized_url},
        {
            "$set": {
                "rating": rating,
                "updated_at": now
            },
            "$setOnInsert": {
                "created_at": now
            }
        },
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return doc


async def get_rating_by_user_and_article_url(user_id: str, article_url: str) -> Optional[dict[str, Any]]:
    doc = await ratings_collection.find_one({
        "user_id": user_id,
        "article_url": normalize_url(article_url)
    })
    return doc


async def get_article_rating_summary(article_url: str) -> dict[str, Any]:
    normalized_url = normalize_url(article_url)
    pipeline = [
        {"$match": {"article_url": normalized_url}},
        {"$group": {
            "_id": None,
            "average_rating": {"$avg": "$rating"},
            "total_ratings": {"$sum": 1}
        }}
    ]
    
    cursor = ratings_collection.aggregate(pipeline)
    results = await cursor.to_list(length=1)
    
    if results:
        result = results[0]
        # Round the average rating to 1 decimal place
        avg_rating = round(result.get("average_rating", 0.0), 1)
        return {
            "average_rating": avg_rating,
            "total_ratings": result.get("total_ratings", 0)
        }
    
    return {
        "average_rating": 0.0,
        "total_ratings": 0
    }


async def delete_rating(user_id: str, article_url: str) -> bool:
    normalized_url = normalize_url(article_url)
    result = await ratings_collection.delete_one({
        "user_id": user_id,
        "article_url": normalized_url
    })
    return result.deleted_count == 1
