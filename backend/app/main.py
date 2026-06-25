from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.database.session import engine
from app.database.base import Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    setup_logging()
    logger.info("Starting AI Research Assistant API Backend...")
    
    # 1. Create upload and chroma data paths if they don't exist
    upload_path = settings.get_upload_path()
    chroma_path = settings.get_chroma_path()
    logger.info(
        "Verifying backend storage paths...",
        upload_dir=str(upload_path),
        chroma_dir=str(chroma_path)
    )

    # 2. In Phase 1, we initialize DB tables directly on startup using SQLAlchemy Base.
    # In later phases, we will introduce Alembic migrations.
    logger.info("Initializing database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error("Failed to initialize database tables.", error=str(e))
        raise e
        
    yield
    
    # Shutdown tasks
    logger.info("Shutting down AI Research Assistant API Backend...")

# Instantiate the FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Set up CORS middleware to allow React frontend connection
# Adjust allow_origins for production deployment later
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, replace with specific origins (e.g., ["http://localhost:5173"])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["Health"])
def health_check():
    """
    Simple API health-check endpoint.
    """
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "debug_mode": settings.DEBUG
    }
