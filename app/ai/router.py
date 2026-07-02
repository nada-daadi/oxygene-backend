"""
AI Router — exposes three public endpoints:

  POST /api/ai/summarize   → SummarizeResponse
  POST /api/ai/translate   → TranslateResponse
  POST /api/ai/read        → ReadResponse

All endpoints are public (no auth token required).
Heavy lifting is delegated to app.ai.service.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from app.ai import service as ai_service
from app.ai.schemas import (
    ReadRequest,
    ReadResponse,
    SummarizeRequest,
    SummarizeResponse,
    TranslateRequest,
    TranslateResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/summarize",
    response_model=SummarizeResponse,
    status_code=status.HTTP_200_OK,
    summary="Summarize a news article using Gemini AI",
)
async def summarize_article(payload: SummarizeRequest) -> SummarizeResponse:
    """
    Accepts the article URL, title and description (scraped on the frontend).
    Returns a concise bullet-point summary in Arabic.
    Responses are cached in MongoDB — subsequent calls are instant.
    """
    try:
        return await ai_service.get_summary(payload)
    except RuntimeError as exc:
        logger.error("Summarize error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Unexpected summarize error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating the summary.",
        )


@router.post(
    "/translate",
    response_model=TranslateResponse,
    status_code=status.HTTP_200_OK,
    summary="Translate a news article using Gemini AI",
)
async def translate_article(payload: TranslateRequest) -> TranslateResponse:
    """
    Translates the article to the requested language (ar / fr / en).
    Cache is keyed by (articleUrl, targetLanguage).
    """
    try:
        return await ai_service.get_translation(payload)
    except RuntimeError as exc:
        logger.error("Translate error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Unexpected translate error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while translating the article.",
        )


@router.post(
    "/read",
    response_model=ReadResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate TTS audio for a news article using Edge-TTS",
)
async def read_article(payload: ReadRequest) -> ReadResponse:
    """
    Generates an MP3 via Edge-TTS, uploads it to Cloudinary, and returns the URL.
    The generated audio is cached per (articleUrl, language).
    """
    try:
        return await ai_service.get_audio(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except RuntimeError as exc:
        logger.error("TTS error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Unexpected TTS error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating audio.",
        )
