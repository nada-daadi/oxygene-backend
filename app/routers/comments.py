import urllib.parse

from fastapi import APIRouter, Depends, Query, status
from fastapi.security import OAuth2PasswordBearer

from app.schemas.comment import CommentCreate, CommentPublic, CommentsPage, CommentUpdate
from app.services.comment_service import (
    create_my_comment,
    delete_my_comment,
    edit_my_comment,
    list_article_comments,
)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


@router.post(
    "/",
    response_model=CommentPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Create a comment (auth required)",
)
async def create_comment(
    payload: CommentCreate,
    token: str = Depends(oauth2_scheme),
):
    return await create_my_comment(token, payload)


@router.get(
    "/article",
    response_model=CommentsPage,
    summary="Get comments for an article (public)",
)
async def get_comments(
    article_url: str = Query(..., description="The URL of the article"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
):
    return await list_article_comments(article_url, page, page_size)


@router.put(
    "/comment/{comment_id}",
    response_model=CommentPublic,
    summary="Edit own comment (auth required)",
)
async def edit_comment(
    comment_id: str,
    payload: CommentUpdate,
    token: str = Depends(oauth2_scheme),
):
    return await edit_my_comment(token, comment_id, payload)


@router.delete(
    "/comment/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete own comment (auth required)",
)
async def delete_comment(
    comment_id: str,
    token: str = Depends(oauth2_scheme),
):
    await delete_my_comment(token, comment_id)