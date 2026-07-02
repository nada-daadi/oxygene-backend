"""
Gemini AI service — wraps google-genai (new SDK) for article summarization
and translation.

Requires:
  GEMINI_API_KEY in .env
"""

import asyncio
import logging
from functools import lru_cache

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)

_LANG_NAMES: dict[str, str] = {
    "ar": "Arabic",
    "fr": "French",
    "en": "English",
}


@lru_cache(maxsize=1)
def _get_client() -> genai.Client:
    """Lazily initialise the Gemini client (cached for the process lifetime)."""
    if not settings.GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to your .env file."
        )
    return genai.Client(api_key=settings.GEMINI_API_KEY)


async def summarize_article(title: str, description: str) -> str:
    """
    Generate a concise, professional Arabic summary for a news article.

    Returns a plain-text summary (3–5 key bullet points).
    Runs the blocking Gemini call in a thread pool to stay async-safe.
    """
    client = _get_client()
    clipped = description[:8_000]

    prompt = (
        "أنت محرر صحفي محترف. لديك المقالة الإخبارية التالية:\n\n"
        f"العنوان: {title}\n\n"
        f"المحتوى:\n{clipped}\n\n"
        "اكتب ملخصاً موجزاً واحترافياً لهذه المقالة باللغة العربية "
        "في شكل 3 إلى 5 نقاط رئيسية. "
        "استخدم رمز '•' في بداية كل نقطة. "
        "لا تُضف أي مقدمة أو خاتمة — فقط النقاط مباشرةً."
    )

    def _call() -> str:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text.strip()

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _call)


async def translate_article(
    title: str,
    description: str,
    target_language: str,
) -> str:
    """
    Translate an article to the target language using Gemini.

    Preserves paragraph structure, headings, names, numbers and dates.
    Returns the translated text as a plain string.
    """
    client = _get_client()
    lang_name = _LANG_NAMES.get(target_language, target_language)
    clipped = description[:10_000]

    prompt = (
        f"You are a professional multilingual journalist. "
        f"Translate the following news article to {lang_name}.\n\n"
        f"Title: {title}\n\n"
        f"Article:\n{clipped}\n\n"
        "Rules:\n"
        "- Preserve all paragraph breaks.\n"
        "- Keep proper nouns, names, numbers and dates unchanged.\n"
        "- Maintain a professional journalistic tone.\n"
        "- Return ONLY the translated text. No preamble, no commentary."
    )

    def _call() -> str:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text.strip()

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _call)
