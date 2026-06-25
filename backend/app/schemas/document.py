from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class DocumentBase(BaseModel):
    filename: str
    file_type: str
    file_size: int
    status: str

class DocumentOut(DocumentBase):
    id: int
    user_id: int
    summary: Optional[str] = None
    keywords: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Pydantic v2 support for SQLAlchemy attributes
    model_config = ConfigDict(from_attributes=True)

class DocumentUploadResponse(BaseModel):
    message: str
    document: DocumentOut
    is_duplicate: bool
