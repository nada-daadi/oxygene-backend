from urllib.parse import unquote

from fastapi import HTTPException, status

from app.repositories.comment_repository import (
    count_comments_by_article,
    count_recent_comments_by_user,
    create_comment,
    delete_comment,
    get_comment_by_id,
    get_comments_by_article,
    serialize_comment,
    update_comment,
)
from app.schemas.comment import CommentCreate, CommentPublic, CommentsPage, CommentUpdate
from app.services.auth_service import get_current_user_from_token

# Max comments a single user can post on the same article within 1 hour
SPAM_LIMIT = 5
SPAM_WINDOW_MINUTES = 60


async def create_my_comment(token: str, payload: CommentCreate) -> CommentPublic:
    current_user = await get_current_user_from_token(token)

    # ── Spam guard ────────────────────────────────────────────────────────────
    recent = await count_recent_comments_by_user(
        user_id=current_user.id,
        article_url=payload.article_url,
        within_minutes=SPAM_WINDOW_MINUTES,
    )
    if recent >= SPAM_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"You have reached the limit of {SPAM_LIMIT} comments "
                f"per article per hour. Please wait before commenting again."
            ),
        )

    doc = await create_comment(
        user_id=current_user.id,
        username=current_user.name,
        article_url=payload.article_url,
        article_title=payload.article_title,
        content=payload.content,
    )
    return CommentPublic(**serialize_comment(doc))


async def list_article_comments(
    article_url: str,
    page: int = 1,
    page_size: int = 20,
) -> CommentsPage:
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 50:
        page_size = 20

    docs = await get_comments_by_article(article_url, page, page_size)
    total = await count_comments_by_article(article_url)
    has_more = (page * page_size) < total

    comments = [CommentPublic(**serialize_comment(doc)) for doc in docs]
    return CommentsPage(
        comments=comments,
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more,
    )


async def edit_my_comment(token: str, comment_id: str, payload: CommentUpdate) -> CommentPublic:
    current_user = await get_current_user_from_token(token)

    existing = await get_comment_by_id(comment_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    if existing["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own comments",
        )

    updated = await update_comment(comment_id, payload.content)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found after update",
        )
    return CommentPublic(**serialize_comment(updated))


async def delete_my_comment(token: str, comment_id: str) -> None:
    current_user = await get_current_user_from_token(token)

    existing = await get_comment_by_id(comment_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    if existing["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own comments",
        )

    deleted = await delete_comment(comment_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment could not be deleted",
        )
