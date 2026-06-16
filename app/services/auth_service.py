from fastapi import HTTPException, status
from jose import JWTError
from pymongo.errors import DuplicateKeyError

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.repositories.favorite_repository import delete_favorites_by_user_id
from app.repositories.user_repository import (
    create_user,
    delete_user,
    get_user_by_email,
    get_user_by_id,
    get_user_by_name,
    serialize_user,
    update_user,
)
from app.schemas.user import TokenResponse, UserCreate, UserLogin, UserPublic, UserUpdate, PasswordChange


def invalid_credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


def duplicate_name_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="A user with this name already exists",
    )


async def register_user(payload: UserCreate) -> UserPublic:
    existing_user = await get_user_by_email(str(payload.email))
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    existing_name = await get_user_by_name(payload.name)
    if existing_name:
        raise duplicate_name_exception()

    try:
        user = await create_user(
            name=payload.name,
            email=str(payload.email),
            hashed_password=hash_password(payload.password),
            phone=payload.phone,
            sexe=payload.sexe,
            adresse=payload.adresse,
        )
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email or name already exists",
        ) from None

    return UserPublic(**serialize_user(user))


async def login_user(payload: UserLogin) -> TokenResponse:
    user = await get_user_by_email(str(payload.email))
    if not user or not verify_password(payload.password, user["hashed_password"]):
        raise invalid_credentials_exception()

    public_user = UserPublic(**serialize_user(user))
    token = create_access_token(subject=public_user.id, extra_claims={"email": public_user.email})
    return TokenResponse(access_token=token, user=public_user)


async def get_current_user_from_token(token: str) -> UserPublic:
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
    except JWTError:
        raise invalid_credentials_exception() from None

    if not user_id:
        raise invalid_credentials_exception()

    user = await get_user_by_id(user_id)
    if not user:
        raise invalid_credentials_exception()

    return UserPublic(**serialize_user(user))


async def update_current_user(token: str, payload: UserUpdate) -> UserPublic:
    current_user = await get_current_user_from_token(token)
    update_data = payload.model_dump(exclude_unset=True)

    if update_data.get("name") is not None:
        existing_name = await get_user_by_name(
            update_data["name"],
            exclude_user_id=current_user.id,
        )
        if existing_name:
            raise duplicate_name_exception()

    try:
        user = await update_user(current_user.id, update_data)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email or name already exists",
        ) from None

    if not user:
        raise invalid_credentials_exception()

    return UserPublic(**serialize_user(user))


async def delete_current_user(token: str) -> None:
    current_user = await get_current_user_from_token(token)
    await delete_favorites_by_user_id(current_user.id)
    deleted = await delete_user(current_user.id)

    if not deleted:
        raise invalid_credentials_exception()


async def logout_current_user(token: str) -> None:
    await get_current_user_from_token(token)


async def change_user_password(token: str, payload: PasswordChange) -> None:
    """Verify current password then update to the new hashed password."""
    current_user = await get_current_user_from_token(token)

    # Fetch raw user document to get hashed_password
    raw_user = await get_user_by_id(current_user.id)
    if not raw_user:
        raise invalid_credentials_exception()

    if not verify_password(payload.current_password, raw_user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    new_hashed = hash_password(payload.new_password)
    await update_user(current_user.id, {"hashed_password": new_hashed})
