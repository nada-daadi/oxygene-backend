from fastapi import APIRouter, Depends, status, UploadFile, File
from fastapi.security import OAuth2PasswordBearer

from app.schemas.user import UserPublic, UserUpdate
from app.services.auth_service import (
    delete_current_user,
    get_current_user_from_token,
    update_current_user,
    update_user_avatar,
)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


@router.get("/me", response_model=UserPublic)
async def get_my_profile(token: str = Depends(oauth2_scheme)):
    return await get_current_user_from_token(token)


@router.patch("/me", response_model=UserPublic)
async def update_my_profile(payload: UserUpdate, token: str = Depends(oauth2_scheme)):
    return await update_current_user(token, payload)


@router.post("/me/avatar", response_model=UserPublic)
async def update_my_avatar(file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    return await update_user_avatar(token, file)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(token: str = Depends(oauth2_scheme)):
    await delete_current_user(token)
