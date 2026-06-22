from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class RatingCreate(BaseModel):
    article_url: str = Field(min_length=1, max_length=2000)
    rating: int = Field(ge=1, le=5)

    @field_validator("article_url", mode="before")
    @classmethod
    def normalize_article_url(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip().rstrip("/")
        return value


class RatingUpdate(BaseModel):
    rating: int = Field(ge=1, le=5)


class RatingPublic(BaseModel):
    id: str
    user_id: str
    article_url: str
    rating: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class RatingSummary(BaseModel):
    average_rating: float
    total_ratings: int
    user_rating: Optional[int] = None
