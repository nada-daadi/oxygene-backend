"""
High-level AI service orchestrator.

Each method:
  1. Checks MongoDB cache.
  2. If hit  → returns cached data immediately.
  3. If miss → calls Gemini / TTS → persists to cache → returns data.
"""

import logging
from datetime import datetime, timezone

from app.ai import cache_service
from app.ai import gemini_service
from app.ai import tts_service
from app.ai.schemas import (
    ReadRequest,
    ReadResponse,
    SummarizeRequest,
    SummarizeResponse,
    TranslateRequest,
    TranslateResponse,
)

logger = logging.getLogger(__name__)


async def get_summary(request: SummarizeRequest) -> SummarizeResponse:
    """
    Return a Gemini-generated summary for the article.
    Hits MongoDB cache first; only calls Gemini on a cache miss.
    """
    cached_text = await cache_service.get_summary_cache(request.articleUrl)

    if cached_text is not None:
        logger.info("Summary cache HIT for %s", request.articleUrl)
        return SummarizeResponse(
            summary=cached_text,
            cached=True,
            generatedAt=datetime.now(tz=timezone.utc),
        )

    logger.info("Summary cache MISS — calling Gemini for %s", request.articleUrl)
    summary_text = await gemini_service.summarize_article(
        title=request.title,
        description=request.description,
    )

    await cache_service.set_summary_cache(request.articleUrl, summary_text)

    return SummarizeResponse(
        summary=summary_text,
        cached=False,
        generatedAt=datetime.now(tz=timezone.utc),
    )


async def get_translation(request: TranslateRequest) -> TranslateResponse:
    """
    Return a Gemini-translated version of the article.
    Cache is keyed by (articleUrl, targetLanguage).
    """
    cached_text = await cache_service.get_translation_cache(
        request.articleUrl, request.targetLanguage
    )

    if cached_text is not None:
        logger.info(
            "Translation cache HIT for %s → %s",
            request.articleUrl,
            request.targetLanguage,
        )
        return TranslateResponse(
            translatedText=cached_text,
            language=request.targetLanguage,
            cached=True,
        )

    logger.info(
        "Translation cache MISS — calling Gemini for %s → %s",
        request.articleUrl,
        request.targetLanguage,
    )
    translated = await gemini_service.translate_article(
        title=request.title,
        description=request.description,
        target_language=request.targetLanguage,
    )

    await cache_service.set_translation_cache(
        request.articleUrl, request.targetLanguage, translated
    )

    return TranslateResponse(
        translatedText=translated,
        language=request.targetLanguage,
        cached=False,
    )


async def get_audio(request: ReadRequest) -> ReadResponse:
    """
    Return a Cloudinary MP3 URL for the article TTS.
    Cache is keyed by (articleUrl, language).
    """
    cached = await cache_service.get_audio_cache(request.articleUrl, request.language)

    if cached is not None:
        logger.info(
            "Audio cache HIT for %s [%s]", request.articleUrl, request.language
        )
        return ReadResponse(
            audioUrl=cached["audioUrl"],
            duration=cached.get("duration"),
            cached=True,
        )

    logger.info(
        "Audio cache MISS — generating TTS for %s [%s]",
        request.articleUrl,
        request.language,
    )

    # Use description; fall back to title if description is empty
    text = request.description.strip() or request.title

    audio_url, duration = await tts_service.generate_speech(
        text=text,
        article_url=request.articleUrl,
        language=request.language,
    )

    await cache_service.set_audio_cache(
        request.articleUrl, request.language, audio_url, duration
    )

    return ReadResponse(
        audioUrl=audio_url,
        duration=duration,
        cached=False,
    )
