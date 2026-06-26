from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.schemas.user import (
    GoogleLoginRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserPublic,
    PasswordChange,
)
from app.services.auth_service import (
    change_user_password,
    get_current_user_from_token,
    google_login,
    login_user,
    logout_current_user,
    register_user,
)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate):
    return await register_user(payload)


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin):
    return await login_user(payload)


@router.post("/token", response_model=TokenResponse)
async def token(form_data: OAuth2PasswordRequestForm = Depends()):
    payload = UserLogin(email=form_data.username, password=form_data.password)
    return await login_user(payload)


@router.get("/me", response_model=UserPublic)
async def me(token: str = Depends(oauth2_scheme)):
    return await get_current_user_from_token(token)


@router.post("/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    await logout_current_user(token)
    return {"message": "Logged out successfully"}


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(payload: PasswordChange, token: str = Depends(oauth2_scheme)):
    """Change the authenticated user's password. Requires current password verification."""
    await change_user_password(token, payload)


@router.post("/google", response_model=TokenResponse)
async def google(payload: GoogleLoginRequest):
    return await google_login(payload)
