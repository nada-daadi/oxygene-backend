from fastapi import HTTPException, status, UploadFile, File
from jose import JWTError
from pymongo.errors import DuplicateKeyError

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from app.core.config import settings
from app.core.cloudinary_client import upload_to_cloudinary

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
from app.schemas.user import (
    GoogleLoginRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserPublic,
    UserUpdate,
    PasswordChange,
)


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
    if not user:
        raise invalid_credentials_exception()

    # Enforce: Google-provider accounts cannot use email/password login
    if user.get("provider") == "google":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use Google Sign-In for this account",
        )

    if not verify_password(payload.password, user["hashed_password"]):
        raise invalid_credentials_exception()

    public_user = UserPublic(**serialize_user(user))
    token = create_access_token(
        subject=public_user.id, extra_claims={"email": public_user.email}
    )
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


async def update_user_avatar(token: str, file: UploadFile) -> UserPublic:
    current_user = await get_current_user_from_token(token)

    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
    if file.content_type not in allowed_types:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Unsupported image type")

    file_bytes = await file.read()
    max_size = 5 * 1024 * 1024  # 5 MB
    if len(file_bytes) > max_size:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Avatar must be 5MB or smaller")

    # Upload to Cloudinary — no eager transformation to keep upload fast
    try:
        result = await upload_to_cloudinary(
            file_bytes,
            public_id=f"avatar_{current_user.id}",
            resource_type="image",
            overwrite=True,
        )
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Failed to upload avatar: {str(e)}")

    # Build a crop+resize URL by injecting the transformation into the secure_url
    # e.g. https://res.cloudinary.com/cloud/image/upload/v123/avatar_xxx.jpg
    #   → https://res.cloudinary.com/cloud/image/upload/c_fill,w_300,h_300/v123/avatar_xxx.jpg
    raw_url: str = result.get("secure_url", "")
    avatar_url = raw_url.replace("/image/upload/", "/image/upload/c_fill,w_300,h_300,q_auto,f_auto/")

    user = await update_user(current_user.id, {
        "avatar_url": avatar_url,
        "avatar_public_id": result.get("public_id"),
    })
    
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


async def _verify_google_id_token(id_token: str) -> dict:
    """
    Verify Google ID token:
    - signature is verified by google-auth
    - audience must match GOOGLE_WEB_CLIENT_ID (strict)
    - email_verified must be true
    """
    try:
        # google-auth verifies signature and decodes claims
        # audience is passed as an allowed audience
        id_info = google_id_token.verify_oauth2_token(
            id_token,
            google_requests.Request(),
            audience=settings.GOOGLE_WEB_CLIENT_ID,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Google Sign-In token",
        ) from e

    # email_verified == true requirement
    if not id_info.get("email_verified", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account email is not verified",
        )

    # strict audience enforcement (must be exactly GOOGLE_WEB_CLIENT_ID)
    if id_info.get("aud") != settings.GOOGLE_WEB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google token audience mismatch",
        )

    return id_info


async def google_login(payload: GoogleLoginRequest) -> TokenResponse:
    id_info = await _verify_google_id_token(payload.id_token)

    google_id = str(id_info.get("sub"))
    email = str(id_info.get("email")).lower()

    # Name from Google (may be absent)
    given_name = id_info.get("given_name") or ""
    family_name = id_info.get("family_name") or ""
    name_from_google = (given_name + (" " if given_name and family_name else "") + family_name).strip()

    if not name_from_google:
        # fallback: use email local-part
        name_from_google = email.split("@")[0].strip() or "Google User"

    # If email exists: always link by email safely without duplicating accounts
    existing_user = await get_user_by_email(email)
    if existing_user:
        # Update provider fields for linking
        user_updates = {
            "provider": "google",
            "google_id": google_id,
            "is_email_verified": True,
            # Do NOT create/change password for google users
        }
        updated = await update_user(str(existing_user["_id"]), user_updates)
        # update_user expects user_id as Mongo ObjectId string; str(existing_user["_id"]) converts the raw ObjectId.
        user_doc = updated or existing_user
    else:
        # Do NOT create hashed_password for Google users
        user_doc = await create_user(
            name=name_from_google,
            email=email,
            hashed_password=None,
            phone=None,
            sexe=None,
            adresse=None,
            provider="google",
            google_id=google_id,
            is_email_verified=True,
        )

    public_user = UserPublic(**serialize_user(user_doc))
    token = create_access_token(
        subject=public_user.id, extra_claims={"email": public_user.email}
    )
    return TokenResponse(access_token=token, user=public_user)


async def change_user_password(token: str, payload: PasswordChange) -> None:
    """Verify current password then update to the new hashed password."""
    current_user = await get_current_user_from_token(token)

    raw_user = await get_user_by_id(current_user.id)
    if not raw_user:
        raise invalid_credentials_exception()

    # Enforce: Password management is blocked for google-provider users
    if raw_user.get("provider") == "google":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password management is handled by Google",
        )

    if not verify_password(payload.current_password, raw_user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    new_hashed = hash_password(payload.new_password)
    await update_user(current_user.id, {"hashed_password": new_hashed})
