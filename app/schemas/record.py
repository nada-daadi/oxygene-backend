from datetime import datetime
from pydantic import BaseModel, ConfigDict


class RecordPublic(BaseModel):
    id: str
    user_id: str
    user_name: str
    source: str
    file_url: str
    format: str
    original_filename: str | None
    duration_seconds: float | None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class RecordListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list[RecordPublic]
