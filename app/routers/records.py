from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.security import OAuth2PasswordBearer

from app.schemas.record import RecordPublic, RecordListResponse
from app.services.record_service import create_record_from_upload, get_records_list, get_my_records

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


@router.post("/recording", response_model=RecordPublic, status_code=status.HTTP_201_CREATED)
async def upload_recording(file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    return await create_record_from_upload(token, file, source="recording")


@router.post("/upload", response_model=RecordPublic, status_code=status.HTTP_201_CREATED)
async def upload_file(file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    return await create_record_from_upload(token, file, source="upload")


@router.get("", response_model=RecordListResponse)
async def list_records(skip: int = 0, limit: int = 50, token: str = Depends(oauth2_scheme)):
    return await get_records_list(token, skip, limit)


@router.get("/me", response_model=RecordListResponse)
async def my_records(skip: int = 0, limit: int = 50, token: str = Depends(oauth2_scheme)):
    return await get_my_records(token, skip, limit)
