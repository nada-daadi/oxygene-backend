from fastapi import HTTPException, status

from app.repositories.share_repository import (
    create_share,
    get_share_stats,
    get_user_shares,
    serialize_share,
)
from app.schemas.share import ShareCreate, ShareLinkResponse, SharePublic, ShareStats
from app.services.auth_service import get_current_user_from_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required to perform this action",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------


async def track_article_share(token: str, payload: ShareCreate) -> SharePublic:
    """
    Validate the JWT, then record the share action in MongoDB.
    Returns the persisted share record.
    """
    try:
        current_user = await get_current_user_from_token(token)
    except HTTPException:
        raise _unauthorized()

    doc = await create_share(
        user_id=current_user.id,
        article_url=payload.article_url,
        article_title=payload.article_title,
        platform=payload.platform,
    )
    return SharePublic(**serialize_share(doc))


async def get_article_share_stats(article_url: str) -> ShareStats:
    """
    Return aggregated share statistics for an article URL.
    Public endpoint — no authentication required.
    """
    from app.schemas.share import normalize_url

    clean_url = normalize_url(article_url)
    stats = await get_share_stats(clean_url)
    return ShareStats(**stats)


async def generate_share_link(token: str, article_url: str) -> ShareLinkResponse:
    """
    Validate the JWT and return a shareable link for the article.
    The share_url is currently the canonical (normalized) article URL.
    Extend this to generate short/deep links if needed later.
    """
    try:
        await get_current_user_from_token(token)
    except HTTPException:
        raise _unauthorized()

    from app.schemas.share import normalize_url

    clean_url = normalize_url(article_url)

    return ShareLinkResponse(
        article_url=clean_url,
        share_url=clean_url,
        article_title="",
    )


async def list_my_shares(token: str) -> list[SharePublic]:
    """Return the current user's share history."""
    try:
        current_user = await get_current_user_from_token(token)
    except HTTPException:
        raise _unauthorized()

    docs = await get_user_shares(current_user.id)
    return [SharePublic(**serialize_share(d)) for d in docs]
