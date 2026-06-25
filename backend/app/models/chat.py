from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.database.base import Base

class ChatSession(Base):
    """
    SQLAlchemy model representing a Conversational Session.
    Enables users to manage multiple isolated chat threads in the sidebar.
    """
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), default="New Chat", nullable=False)
    
    # Audit Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    """
    SQLAlchemy model representing an individual message exchange.
    Tracks role ('user' or 'assistant') and persists inline RAG citations.
    """
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_session.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False)           # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    citations = Column(Text, nullable=True)             # JSON-serialized metadata string of cited sources
    
    # Audit Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")
