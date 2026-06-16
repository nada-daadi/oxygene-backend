from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


def _strip_html(value: str) -> str:
    """Remove any HTML tags from user input (XSS prevention)."""
    import re
    return re.sub(r'<[^>]+>', '', value).strip()


class CommentCreate(BaseModel):
    article_url: str = Field(min_length=1, max_length=2000)
    article_title: str = Field(default="", max_length=500)
    content: str = Field(min_length=1, max_length=1000)

    @field_validator("article_url", mode="before")
    @classmethod
    def normalize_article_url(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip().rstrip("/")
        return value

    @field_validator("content", mode="before")
    @classmethod
    def sanitize_content(cls, value: str) -> str:
        if isinstance(value, str):
            return _strip_html(value)
        return value

    @field_validator("article_title", mode="before")
    @classmethod
    def sanitize_title(cls, value: str) -> str:
        if isinstance(value, str):
            return _strip_html(value)
        return value


class CommentUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=1000)

    @field_validator("content", mode="before")
    @classmethod
    def sanitize_content(cls, value: str) -> str:
        if isinstance(value, str):
            return _strip_html(value)
        return value


class CommentPublic(BaseModel):
    id: str
    user_id: str
    username: str
    article_url: str
    article_title: str
    content: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class CommentsPage(BaseModel):
    comments: list[CommentPublic]
    total: int
    page: int
    page_size: int
    has_more: bool
