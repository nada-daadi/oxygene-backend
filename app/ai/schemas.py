"""
Pydantic schemas for the AI module (Summarize, Translate, Read Aloud).
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ── Summarize ────────────────────────────────────────────────────────────────


class SummarizeRequest(BaseModel):
    articleUrl: str = Field(..., description="Canonical URL of the article (used as cache key)")
    title: str = Field(..., description="Article title")
    description: str = Field(..., description="Full article text scraped by frontend")


class SummarizeResponse(BaseModel):
    summary: str
    cached: bool = False
    generatedAt: datetime


# ── Translate ─────────────────────────────────────────────────────────────────


class TranslateRequest(BaseModel):
    articleUrl: str = Field(..., description="Canonical URL of the article (used as cache key)")
    title: str
    description: str = Field(..., description="Full article text scraped by frontend")
    targetLanguage: Literal["ar", "fr", "en"] = Field(
        ..., description="Target language code"
    )


class TranslateResponse(BaseModel):
    translatedText: str
    language: str
    cached: bool = False


# ── Read Aloud ────────────────────────────────────────────────────────────────


class ReadRequest(BaseModel):
    articleUrl: str = Field(..., description="Canonical URL of the article (used as cache key)")
    title: str
    description: str = Field(..., description="Full article text scraped by frontend")
    language: Literal["ar", "fr", "en"] = Field(
        default="ar", description="Language of the text (determines TTS voice)"
    )


class ReadResponse(BaseModel):
    audioUrl: str
    duration: Optional[float] = None
    cached: bool = False
