from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password

class AuthService:
    """
    Business service layer managing User authentication and database CRUD operations.
    """
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """
        Retrieves a user by their unique database primary key ID.
        """
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """
        Retrieves a user by their unique email address.
        """
        return db.query(User).filter(User.email == email).first()

    @classmethod
    def register_user(cls, db: Session, user_in: UserCreate) -> User:
        """
        Registers a new user after verifying that the email address is unique.
        Raises a ValueError if the email is already registered.
        """
        existing_user = cls.get_user_by_email(db, email=user_in.email)
        if existing_user:
            raise ValueError(f"The email '{user_in.email}' is already registered in the system.")
            
        hashed_password = get_password_hash(user_in.password)
        db_user = User(
            email=user_in.email,
            hashed_password=hashed_password,
            full_name=user_in.full_name,
            is_active=user_in.is_active,
            is_superuser=user_in.is_superuser
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @classmethod
    def authenticate_user(cls, db: Session, email: str, password: str) -> Optional[User]:
        """
        Authenticates a user email and password.
        Returns the User instance if successful, or None if authentication fails.
        """
        user = cls.get_user_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    @classmethod
    def update_user(cls, db: Session, db_user: User, user_in: UserUpdate) -> User:
        """
        Updates a user record with the provided update data fields.
        """
        update_data = user_in.model_dump(exclude_unset=True)
        if "password" in update_data and update_data["password"]:
            hashed_password = get_password_hash(update_data["password"])
            db_user.hashed_password = hashed_password
            
        for field, value in update_data.items():
            if field != "password":
                setattr(db_user, field, value)
                
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
