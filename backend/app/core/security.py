from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union
# pyright: ignore [reportMissingImports]
import jwt
# pyright: ignore [reportMissingImports]
import bcrypt
from app.core.config import settings

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain text password against its corresponding hashed version
    using the bcrypt library directly.
    """
    try:
        # Convert inputs to bytes as required by the bcrypt library
        plain_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception:
        # Returns False if decoding or verification fails (e.g., malformed hash format)
        return False

def get_password_hash(password: str) -> str:
    """
    Hashes a plain text password using bcrypt with a generated salt.
    """
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")

def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Generates a signed HS256 JWT access token.
    The payload includes the user id (subject 'sub') and expiration timestamp ('exp').
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {
        "exp": expire,
        "sub": str(subject)
    }
    
    # Sign the token using our secret key and selected HS256 algorithm
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt
