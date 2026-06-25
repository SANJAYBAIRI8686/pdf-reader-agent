from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.database.base import Base

class Document(Base):
    """
    SQLAlchemy model representing an uploaded document.
    Maps details of PDF, DOCX, and MD files stored on disk and vector databases.
    """
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    
    filename = Column(String(255), nullable=False)
    filepath = Column(String(512), nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)  # MD5 checksum for duplicate check
    file_size = Column(Integer, nullable=False)                 # File size in bytes
    file_type = Column(String(50), nullable=False)              # e.g., 'pdf', 'docx', 'md'
    status = Column(String(50), default="processing", nullable=False)  # 'processing', 'processed', 'failed'
    
    # Text metadata stubs (generated asynchronously in background)
    summary = Column(Text, nullable=True)
    keywords = Column(Text, nullable=True)                       # Comma-separated list
    
    # Audit Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="documents")

# We will import the relationship in app/models/user.py to ensure bi-directional linking.
