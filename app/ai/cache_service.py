"""
MongoDB-backed cache for AI responses.

Collection: ai_cache
Document shape:
  {
    articleUrl: str,        # primary cache key
    language: str | None,   # "ar" / "fr" / "en" — only for translations
    type: str,              # "summary" | "translation" | "audio"
    summary: str | None,
    translatedText: str | None,
    audioUrl: str | None,
    duration: float | None,
    createdAt: datetime,
    updatedAt: datetime,
  }

Compound indexes ensure each (articleUrl, type, language?) is unique.
"""

from datetime import datetime, timezone
from typing import Optional

from app.core.database import database

_collection = database["ai_cache"]


# ── Index Setup ───────────────────────────────────────────────────────────────


async def create_ai_cache_indexes() -> None:
    """Create sparse compound indexes on the ai_cache collection."""
    await _collection.create_index(
        [("articleUrl", 1), ("type", 1)],
        name="idx_url_type",
        sparse=True,
    )
    await _collection.create_index(
        [("articleUrl", 1), ("type", 1), ("language", 1)],
        name="idx_url_type_lang",
        sparse=True,
    )
    print("✅ ai_cache indexes created")


# ── Helpers ───────────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


# ── Summary Cache ─────────────────────────────────────────────────────────────


async def get_summary_cache(article_url: str) -> Optional[str]:
    """Return cached summary text, or None if not cached."""
    doc = await _collection.find_one(
        {"articleUrl": article_url, "type": "summary"},
        {"summary": 1},
    )
    return doc["summary"] if doc else None


async def set_summary_cache(article_url: str, summary: str) -> None:
    """Upsert summary into cache."""
    await _collection.update_one(
        {"articleUrl": article_url, "type": "summary"},
        {
            "$set": {
                "summary": summary,
                "updatedAt": _now(),
            },
            "$setOnInsert": {
                "articleUrl": article_url,
                "type": "summary",
                "createdAt": _now(),
            },
        },
        upsert=True,
    )


# ── Translation Cache ─────────────────────────────────────────────────────────


async def get_translation_cache(article_url: str, language: str) -> Optional[str]:
    """Return cached translated text, or None if not cached."""
    doc = await _collection.find_one(
        {"articleUrl": article_url, "type": "translation", "language": language},
        {"translatedText": 1},
    )
    return doc["translatedText"] if doc else None


async def set_translation_cache(
    article_url: str, language: str, translated_text: str
) -> None:
    """Upsert translation into cache."""
    await _collection.update_one(
        {"articleUrl": article_url, "type": "translation", "language": language},
        {
            "$set": {
                "translatedText": translated_text,
                "language": language,
                "updatedAt": _now(),
            },
            "$setOnInsert": {
                "articleUrl": article_url,
                "type": "translation",
                "createdAt": _now(),
            },
        },
        upsert=True,
    )


# ── Audio Cache ───────────────────────────────────────────────────────────────


async def get_audio_cache(
    article_url: str, language: str
) -> Optional[dict]:
    """Return cached audio info dict {audioUrl, duration}, or None."""
    doc = await _collection.find_one(
        {"articleUrl": article_url, "type": "audio", "language": language},
        {"audioUrl": 1, "duration": 1},
    )
    if doc:
        return {"audioUrl": doc["audioUrl"], "duration": doc.get("duration")}
    return None


async def set_audio_cache(
    article_url: str, language: str, audio_url: str, duration: Optional[float]
) -> None:
    """Upsert audio info into cache."""
    await _collection.update_one(
        {"articleUrl": article_url, "type": "audio", "language": language},
        {
            "$set": {
                "audioUrl": audio_url,
                "duration": duration,
                "language": language,
                "updatedAt": _now(),
            },
            "$setOnInsert": {
                "articleUrl": article_url,
                "type": "audio",
                "createdAt": _now(),
            },
        },
        upsert=True,
    )
