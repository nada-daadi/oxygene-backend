from fastapi import APIRouter, Depends, Query, status
from fastapi.security import OAuth2PasswordBearer

from app.schemas.share import ShareCreate, ShareLinkResponse, SharePublic, ShareStats
from app.services.share_service import (
    generate_share_link,
    get_article_share_stats,
    list_my_shares,
    track_article_share,
)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


# ---------------------------------------------------------------------------
# Protected endpoints (require JWT)
# ---------------------------------------------------------------------------


@router.post(
    "/track",
    response_model=SharePublic,
    status_code=status.HTTP_201_CREATED,
    summary="Track an article share",
    description=(
        "Records a share action for a scraped article identified by its URL. "
        "Requires authentication — returns 401 if the token is missing or invalid."
    ),
)
async def track_share(
    payload: ShareCreate,
    token: str = Depends(oauth2_scheme),
) -> SharePublic:
    return await track_article_share(token, payload)


@router.post(
    "/link",
    response_model=ShareLinkResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a shareable link",
    description=(
        "Returns a normalized, tracking-parameter-free shareable URL for the article. "
        "Requires authentication."
    ),
)
async def get_share_link(
    article_url: str = Query(..., min_length=10, max_length=2048, description="Raw article URL"),
    token: str = Depends(oauth2_scheme),
) -> ShareLinkResponse:
    return await generate_share_link(token, article_url)


@router.get(
    "/me",
    response_model=list[SharePublic],
    status_code=status.HTTP_200_OK,
    summary="Get my share history",
    description="Returns the current user's most recent share records (up to 100).",
)
async def my_shares(
    token: str = Depends(oauth2_scheme),
) -> list[SharePublic]:
    return await list_my_shares(token)


# ---------------------------------------------------------------------------
# Public endpoints (no auth required)
# ---------------------------------------------------------------------------


@router.get(
    "/stats",
    response_model=ShareStats,
    status_code=status.HTTP_200_OK,
    summary="Get share statistics for an article",
    description=(
        "Returns total share count and breakdown by platform for a given article URL. "
        "Public endpoint — no authentication required."
    ),
)
async def share_stats(
    article_url: str = Query(..., min_length=10, max_length=2048, description="Article URL"),
) -> ShareStats:
    return await get_article_share_stats(article_url)
