from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict

# Shared properties
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = True
    is_superuser: bool = False

# Schema for creating a User via the API
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=100, description="User password (min 8 characters)")

# Schema for updating a User (all fields optional)
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=100)
    full_name: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None

# Schema for returning User profile data to the client (filtering out password)
class UserOut(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    # Pydantic v2 configuration to allow serialization of SQLAlchemy model instances
    model_config = ConfigDict(from_attributes=True)

# Login Schema
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Token response schema
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Schema representing data embedded in the JWT payload
class TokenData(BaseModel):
    id: Optional[int] = None
