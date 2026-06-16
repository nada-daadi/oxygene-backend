from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class FavoriteCreate(BaseModel):
    article_id: str = Field(min_length=1, max_length=100)

    @field_validator("article_id", mode="before")
    @classmethod
    def normalize_article_id(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value


class FavoritePublic(BaseModel):
    id: str
    user_id: str
    article_id: str
    created_at: datetime


class FavoriteStatus(BaseModel):
    article_id: str
    is_favorite: bool
