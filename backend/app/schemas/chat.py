import json
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict

# --- Chat Session Schemas ---

class ChatSessionBase(BaseModel):
    title: str = Field(default="New Chat", max_length=255)

class ChatSessionCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)

class ChatSessionOut(ChatSessionBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Chat Message Schemas ---

class ChatMessageBase(BaseModel):
    role: str = Field(description="Role: 'user' or 'assistant'")
    content: str

class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1, description="Text prompt content from user")

class ChatMessageOut(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    citations: Optional[List[dict[str, Any]]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    # Automatically parse the database stringified JSON field into a structured list
    @field_validator("citations", mode="before")
    @classmethod
    def parse_db_citations(cls, v: Any) -> Any:
        if isinstance(v, str) and v.strip():
            try:
                return json.loads(v)
            except Exception:
                return []
        return v or []

# --- Custom Query & Search Schemas ---

class SemanticSearchHit(BaseModel):
    text: str
    filename: str
    document_id: int
    score: float

class QueryResponse(BaseModel):
    answer: str
    citations: List[dict[str, Any]]
