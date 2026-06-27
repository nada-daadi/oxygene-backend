import time
from fastapi import UploadFile, HTTPException, status
from app.services.auth_service import get_current_user_from_token
from app.core.cloudinary_client import upload_to_cloudinary
from app.repositories.record_repository import (
    create_record, 
    list_records, 
    count_records, 
    serialize_record,
    list_records_by_user,
    count_records_by_user
)
from app.schemas.record import RecordPublic, RecordListResponse

ALLOWED_MIME_TYPES = ["audio/mpeg", "audio/mp4", "audio/x-m4a", "audio/3gpp", "video/mp4"]
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB

async def create_record_from_upload(token: str, file: UploadFile, source: str) -> RecordPublic:
    # 1. Auth gate: reject guests with 401 via existing exception
    current_user = await get_current_user_from_token(token)

    # 2. Validate content type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type"
        )

    # 3. Enforce max upload size by reading in chunks
    file_bytes = b""
    chunk_size = 1024 * 1024  # 1 MB
    while chunk := await file.read(chunk_size):
        file_bytes += chunk
        if len(file_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size exceeds the maximum limit of 25 MB"
            )

    # 4. Upload to Cloudinary
    public_id = f"{current_user.id}_{int(time.time())}"
    try:
        cloudinary_response = await upload_to_cloudinary(
            file_bytes=file_bytes,
            public_id=public_id,
            resource_type="video"  # Cloudinary requires "video" for audio files too
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )

    # 5. Persist via create_record
    record = await create_record(
        user_id=current_user.id,
        user_name=current_user.name,
        source=source,
        file_url=cloudinary_response.get("secure_url"),
        cloudinary_public_id=cloudinary_response.get("public_id"),
        resource_type=cloudinary_response.get("resource_type", "video"),
        format=cloudinary_response.get("format", ""),
        original_filename=file.filename,
        duration_seconds=cloudinary_response.get("duration")
    )

    # 6. Return RecordPublic
    return RecordPublic(**serialize_record(record))


async def get_records_list(token: str, skip: int, limit: int) -> RecordListResponse:
    # Protect list view as well (based on user's open question #2 feedback)
    await get_current_user_from_token(token)
    
    total = await count_records()
    records = await list_records(skip, limit)
    
    items = [RecordPublic(**serialize_record(r)) for r in records]
    
    return RecordListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=items
    )


async def get_my_records(token: str, skip: int, limit: int) -> RecordListResponse:
    current_user = await get_current_user_from_token(token)
    
    total = await count_records_by_user(current_user.id)
    records = await list_records_by_user(current_user.id, skip, limit)
    
    items = [RecordPublic(**serialize_record(r)) for r in records]
    
    return RecordListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=items
    )
