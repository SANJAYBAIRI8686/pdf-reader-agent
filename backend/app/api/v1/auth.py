from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.user import UserCreate, UserOut, Token
from app.services.auth_service import AuthService
from app.core.security import create_access_token
from app.api.deps import get_current_user
from app.models.user import User

# Initialize the API router for authentication endpoints
router = APIRouter()

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate
) -> Any:
    """
    Register a new user in the system.
    """
    try:
        user = AuthService.register_user(db, user_in=user_in)
        return user
    except ValueError as e:
        # Map domain exceptions (like email already registered) to HTTP 400 Bad Request
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login", response_model=Token)
def login_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, retrieve a JWT access token.
    FastAPI expects 'username' and 'password' fields in a URL-encoded form request.
    """
    user = AuthService.authenticate_user(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
        
    # Generate token payload signed with user ID as subject ('sub')
    access_token = create_access_token(subject=user.id)
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=UserOut)
def read_user_me(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get current logged in user profile.
    Requires header: Authorization: Bearer <JWT>
    """
    return current_user
