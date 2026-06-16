from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordBearer

from app.schemas.favorite import FavoriteCreate, FavoritePublic, FavoriteStatus
from app.services.favorite_service import (
    add_my_favorite,
    get_my_favorite_status,
    list_my_favorites,
    remove_my_favorite,
)


router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


@router.get("/", response_model=list[FavoritePublic])
async def get_my_favorites(token: str = Depends(oauth2_scheme)):
    return await list_my_favorites(token)


@router.post("/", response_model=FavoritePublic, status_code=status.HTTP_201_CREATED)
async def create_my_favorite(
    payload: FavoriteCreate,
    token: str = Depends(oauth2_scheme),
):
    return await add_my_favorite(token, payload)


@router.get("/{article_id}/status", response_model=FavoriteStatus)
async def get_favorite_status(
    article_id: str,
    token: str = Depends(oauth2_scheme),
):
    return await get_my_favorite_status(token, article_id)


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_favorite(
    article_id: str,
    token: str = Depends(oauth2_scheme),
):
    await remove_my_favorite(token, article_id)
