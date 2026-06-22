from typing import Any, Optional
from fastapi import HTTPException, status

from app.repositories import rating_repository
from app.schemas.rating import RatingCreate, RatingSummary
from app.services.auth_service import get_current_user_from_token


class RatingService:
    @staticmethod
    async def create_or_update_rating(token: str, payload: RatingCreate) -> RatingSummary:
        """
        Creates or updates a user's rating for an article.
        Returns the updated rating summary.
        """
        current_user = await get_current_user_from_token(token)
        
        await rating_repository.create_or_update_rating(
            user_id=current_user.id,
            article_url=payload.article_url,
            rating=payload.rating
        )
        
        return await RatingService.get_rating_summary(token, payload.article_url)

    @staticmethod
    async def get_rating_summary(token: Optional[str], article_url: str) -> RatingSummary:
        """
        Retrieves the average rating, total ratings, and optionally the current user's rating.
        """
        summary = await rating_repository.get_article_rating_summary(article_url)
        
        user_rating_val = None
        if token:
            try:
                current_user = await get_current_user_from_token(token)
                user_rating_doc = await rating_repository.get_rating_by_user_and_article_url(
                    user_id=current_user.id,
                    article_url=article_url
                )
                if user_rating_doc:
                    user_rating_val = user_rating_doc.get("rating")
            except Exception:
                # If token is invalid or expired, just return the summary without user_rating
                pass
                
        return RatingSummary(
            average_rating=summary["average_rating"],
            total_ratings=summary["total_ratings"],
            user_rating=user_rating_val
        )

    @staticmethod
    async def delete_rating(token: str, article_url: str) -> RatingSummary:
        """
        Deletes a user's rating for an article and returns the updated summary.
        """
        current_user = await get_current_user_from_token(token)
        
        deleted = await rating_repository.delete_rating(
            user_id=current_user.id,
            article_url=article_url
        )
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rating not found for this user and article."
            )
            
        return await RatingService.get_rating_summary(token, article_url)

rating_service = RatingService()
