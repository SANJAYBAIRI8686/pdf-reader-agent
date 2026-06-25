from typing import Generator
# pyright: ignore [reportMissingImports]
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.core.config import settings
from app.database.session import get_db
from app.services.auth_service import AuthService
from app.models.user import User
from app.schemas.user import TokenData

# Define the OAuth2 security scheme.
# It points to the /auth/login route which we will create next.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    FastAPI dependency that decodes the JWT access token and yields
    the authenticated User instance. Raises HTTP 401/403 if invalid.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode the JWT token signature using our app settings key
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
            
        token_data = TokenData(id=int(user_id_str))
    except (jwt.PyJWTError, ValidationError, ValueError):
        raise credentials_exception
        
    user = AuthService.get_user_by_id(db, user_id=token_data.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
        
    return user

def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency that guarantees the current user has superuser privileges.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have enough privileges"
        )
    return current_user
