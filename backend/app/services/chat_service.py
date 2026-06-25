import json
from typing import List, Optional, Any
from sqlalchemy.orm import Session
from app.models.chat import ChatSession, ChatMessage
from app.core.logging import logger

class ChatService:
    """
    Service layer coordinating ChatSession and ChatMessage database CRUD operations.
    """
    
    @staticmethod
    def get_session(db: Session, session_id: int) -> Optional[ChatSession]:
        """
        Retrieves a ChatSession record by its primary key ID.
        """
        return db.query(ChatSession).filter(ChatSession.id == session_id).first()

    @staticmethod
    def get_user_sessions(db: Session, user_id: int) -> List[ChatSession]:
        """
        Retrieves all ChatSession records created by a specific user.
        Sorts sessions from newest to oldest.
        """
        return db.query(ChatSession).filter(
            ChatSession.user_id == user_id
        ).order_by(ChatSession.created_at.desc()).all()

    @classmethod
    def create_session(cls, db: Session, user_id: int, title: Optional[str] = None) -> ChatSession:
        """
        Starts a new ChatSession thread.
        """
        default_title = title or "New Chat"
        session = ChatSession(
            user_id=user_id,
            title=default_title
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        logger.info("Created new chat session", session_id=session.id, user_id=user_id)
        return session

    @classmethod
    def delete_session(cls, db: Session, session: ChatSession) -> bool:
        """
        Deletes a chat session, which cascades and deletes all session messages.
        """
        try:
            db.delete(session)
            db.commit()
            logger.info("Deleted chat session registry", session_id=session.id)
            return True
        except Exception as e:
            logger.error("Failed to delete chat session", session_id=session.id, error=str(e))
            db.rollback()
            return False

    @classmethod
    def create_message(
        cls,
        db: Session,
        session_id: int,
        role: str,
        content: str,
        citations: Optional[List[Any]] = None
    ) -> ChatMessage:
        """
        Logs a user prompt or assistant response.
        Converts the citations list into a stringified JSON before committing.
        """
        citations_json = None
        if citations:
            citations_json = json.dumps(citations)
            
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            citations=citations_json
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    @classmethod
    def get_session_messages(cls, db: Session, session_id: int) -> List[ChatMessage]:
        """
        Retrieves all logged messages belonging to a chat session, sorted chronologically.
        """
        return db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at.asc()).all()

    @classmethod
    def update_session_title(cls, db: Session, session: ChatSession, new_title: str) -> ChatSession:
        """
        Updates the title display string of a session.
        Useful for dynamically renaming the session from the first prompt.
        """
        session.title = new_title
        db.add(session)
        db.commit()
        db.refresh(session)
        return session
