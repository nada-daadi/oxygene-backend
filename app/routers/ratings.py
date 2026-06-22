from typing import Any, Optional
from fastapi import APIRouter, Depends, Query, status
from fastapi.security import OAuth2PasswordBearer

from app.schemas.rating import RatingCreate, RatingSummary
from app.services.rating_service import rating_service

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


@router.post("/", response_model=RatingSummary, status_code=status.HTTP_200_OK)
async def rate_article(
    payload: RatingCreate,
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="/api/auth/token"))
) -> Any:
    """
    Rate an article or update an existing rating (auth required).
    """
    return await rating_service.create_or_update_rating(
        token=token,
        payload=payload
    )


@router.get("/", response_model=RatingSummary)
async def get_article_rating(
    article_url: str = Query(..., description="The URL of the article"),
    token: Optional[str] = Depends(oauth2_scheme)
) -> Any:
    """
    Get the rating summary for an article (average and total).
    If authenticated, also returns the current user's rating.
    """
    return await rating_service.get_rating_summary(
        token=token,
        article_url=article_url
    )


@router.delete("/", response_model=RatingSummary)
async def delete_article_rating(
    article_url: str = Query(..., description="The URL of the article"),
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="/api/auth/token"))
) -> Any:
    """
    Remove the user's rating for an article (auth required).
    """
    return await rating_service.delete_rating(
        token=token,
        article_url=article_url
    )