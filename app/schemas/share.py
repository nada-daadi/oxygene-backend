from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Supported sharing platforms
SharePlatform = Literal[
    "whatsapp",
    "facebook",
    "messenger",
    "telegram",
    "email",
    "copy_link",
    "instagram_story",
    "other",
]


def normalize_url(url: str) -> str:
    """Strip common tracking query parameters from a URL."""
    from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

    tracking_params = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "ref", "referrer", "fbclid", "gclid", "mc_cid", "mc_eid",
        "source", "_ga", "igshid",
    }
    parsed = urlparse(url.strip())
    qs = parse_qs(parsed.query, keep_blank_values=True)
    clean_qs = {k: v for k, v in qs.items() if k not in tracking_params}
    clean_query = urlencode(clean_qs, doseq=True)
    return urlunparse(parsed._replace(query=clean_query))


class ShareCreate(BaseModel):
    """Payload sent by the client when tracking a share action."""

    article_url: str = Field(min_length=10, max_length=2048)
    article_title: str = Field(default="", max_length=500)
    platform: SharePlatform = "other"

    @field_validator("article_url", mode="before")
    @classmethod
    def normalize_article_url(cls, value: str) -> str:
        if isinstance(value, str):
            return normalize_url(value)
        return value

    @field_validator("article_title", mode="before")
    @classmethod
    def trim_title(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value


class SharePublic(BaseModel):
    """Share record returned to the client."""

    id: str
    user_id: str
    article_url: str
    article_title: str
    platform: str
    shared_at: datetime


class ShareStats(BaseModel):
    """Aggregated share statistics for an article."""

    article_url: str
    total_shares: int
    shares_by_platform: dict[str, int]


class ShareLinkResponse(BaseModel):
    """Response for the generate-share-link endpoint."""

    article_url: str
    share_url: str
    article_title: str
