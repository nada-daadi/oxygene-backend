from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.repositories.favorite_repository import (
    add_favorite,
    get_favorite_by_article,
    get_user_favorites,
    remove_favorite,
    serialize_favorite,
)
from app.schemas.favorite import FavoriteCreate, FavoritePublic, FavoriteStatus
from app.services.auth_service import get_current_user_from_token


async def list_my_favorites(token: str) -> list[FavoritePublic]:
    current_user = await get_current_user_from_token(token)
    favorites = await get_user_favorites(current_user.id)
    return [FavoritePublic(**serialize_favorite(favorite)) for favorite in favorites]


async def add_my_favorite(token: str, payload: FavoriteCreate) -> FavoritePublic:
    current_user = await get_current_user_from_token(token)

    try:
        favorite = await add_favorite(current_user.id, payload.article_id)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Article is already in favorites",
        ) from None

    return FavoritePublic(**serialize_favorite(favorite))


async def remove_my_favorite(token: str, article_id: str) -> None:
    current_user = await get_current_user_from_token(token)
    removed = await remove_favorite(current_user.id, article_id)

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favorite not found",
        )


async def get_my_favorite_status(token: str, article_id: str) -> FavoriteStatus:
    current_user = await get_current_user_from_token(token)
    favorite = await get_favorite_by_article(current_user.id, article_id)
    return FavoriteStatus(article_id=article_id.strip(), is_favorite=favorite is not None)
