"""
TTS service using edge-tts.

Generates MP3 audio from article text, uploads to Cloudinary (permanent URL),
and returns the public URL plus approximate duration.

Voice map (by language code):
  ar → ar-SA-ZariyahNeural  (female, clear MSA)
  fr → fr-FR-DeniseNeural
  en → en-US-JennyNeural
"""

import asyncio
import hashlib
import logging
import os
import tempfile
from typing import Optional

import cloudinary
import cloudinary.uploader
import edge_tts

logger = logging.getLogger(__name__)

_VOICE_MAP: dict[str, str] = {
    "ar": "ar-SA-ZariyahNeural",
    "fr": "fr-FR-DeniseNeural",
    "en": "en-US-JennyNeural",
}

# Maximum characters sent to TTS (keep audio under ~10 min)
_MAX_TTS_CHARS = 4_000


def _select_voice(language: str) -> str:
    return _VOICE_MAP.get(language, _VOICE_MAP["ar"])


def _sanitize_text(text: str) -> str:
    """Strip excessive whitespace and clip to TTS limit."""
    cleaned = " ".join(text.split())
    return cleaned[:_MAX_TTS_CHARS]


def _make_public_id(article_url: str, language: str) -> str:
    """Stable Cloudinary public_id derived from the article URL + language."""
    digest = hashlib.sha256(f"{article_url}:{language}".encode()).hexdigest()[:20]
    return f"oxygene_tts/{digest}"


async def generate_speech(
    text: str,
    article_url: str,
    language: str = "ar",
) -> tuple[str, Optional[float]]:
    """
    Generate TTS audio and upload it to Cloudinary.

    Returns:
        (cloudinary_url, duration_seconds)

    Raises:
        RuntimeError on TTS or upload failure.
    """
    sanitized = _sanitize_text(text)
    if not sanitized:
        raise ValueError("Text is empty after sanitization — cannot generate speech.")

    voice = _select_voice(language)
    public_id = _make_public_id(article_url, language)

    # Write to a temporary file so we can upload it
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # ── Generate MP3 with edge-tts ─────────────────────────────────────
        communicate = edge_tts.Communicate(sanitized, voice)
        await communicate.save(tmp_path)

        file_size = os.path.getsize(tmp_path)
        if file_size == 0:
            raise RuntimeError("edge-tts produced an empty audio file.")

        # Estimate duration: average ~150 words/min → ~900 chars/min
        word_count = len(sanitized.split())
        estimated_duration = round((word_count / 150) * 60, 1)

        # ── Upload to Cloudinary ───────────────────────────────────────────
        def _upload() -> str:
            result = cloudinary.uploader.upload(
                tmp_path,
                resource_type="video",   # Cloudinary uses "video" for audio
                public_id=public_id,
                overwrite=True,
                format="mp3",
            )
            return result["secure_url"]

        loop = asyncio.get_event_loop()
        audio_url = await loop.run_in_executor(None, _upload)

        logger.info("TTS uploaded to Cloudinary: %s", audio_url)
        return audio_url, estimated_duration

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
