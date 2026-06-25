import sys
from pathlib import Path

# Add the backend directory to sys.path to enable importing app module
sys.path.append(str(Path(__file__).resolve().parent))

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.database.session import SessionLocal, engine
from app.database.base import Base
from app.models.user import User

def verify_infrastructure():
    setup_logging()
    logger.info("Initializing infrastructure diagnostic checks...")
    
    # 1. Config Check
    logger.info("Checking configurations...")
    logger.info(f"App Name: {settings.APP_NAME}")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"Database URL: {settings.DATABASE_URL}")
    
    # 2. Database Initialization
    logger.info("Creating database tables if not exists...")
    Base.metadata.create_all(bind=engine)
    logger.info("Tables created.")
    
    # 3. Read/Write Operation Check
    logger.info("Verifying database read/write actions...")
    db = SessionLocal()
    try:
        # Create dummy user
        test_email = "diagnostic_test_user@example.com"
        
        # Check if user already exists from previous runs and clean it up
        existing_user = db.query(User).filter(User.email == test_email).first()
        if existing_user:
            logger.info("Cleaning up pre-existing diagnostic user...")
            db.delete(existing_user)
            db.commit()
            
        # Create new user
        new_user = User(
            email=test_email,
            hashed_password="not-a-real-hash-yet-just-testing-db-connection",
            full_name="Diagnostic Assistant",
            is_active=True
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        logger.info("Successfully created new User in DB.", user_id=new_user.id, email=new_user.email)
        
        # Verify read query
        fetched_user = db.query(User).filter(User.id == new_user.id).first()
        assert fetched_user is not None
        assert fetched_user.email == test_email
        logger.info("Successfully verified User retrieval query.")
        
        # Clean up
        db.delete(fetched_user)
        db.commit()
        logger.info("Successfully cleaned up diagnostic User.")
        logger.info("ALL INFRASTRUCTURE DIAGNOSTIC CHECKS PASSED.")
        
    except Exception as e:
        logger.error("Infrastructure diagnostic check FAILED.", error=str(e))
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    verify_infrastructure()
