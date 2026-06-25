import os
import hashlib
from typing import List, Optional
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.document import Document
from app.core.config import settings
from app.core.logging import logger

class DocumentService:
    """
    Service layer coordinating document database status and filesystem persistence.
    """
    
    @staticmethod
    def get_document_by_id(db: Session, doc_id: int) -> Optional[Document]:
        """
        Retrieve a document record by its primary key ID.
        """
        return db.query(Document).filter(Document.id == doc_id).first()

    @staticmethod
    def get_user_documents(db: Session, user_id: int) -> List[Document]:
        """
        Retrieve all document records uploaded by a specific user.
        """
        return db.query(Document).filter(Document.user_id == user_id).all()

    @staticmethod
    def get_document_by_hash(db: Session, user_id: int, file_hash: str) -> Optional[Document]:
        """
        Checks if a user has already uploaded a document with the exact same content hash.
        """
        return db.query(Document).filter(
            Document.user_id == user_id,
            Document.file_hash == file_hash
        ).first()

    @staticmethod
    def calculate_md5(file_content: bytes) -> str:
        """
        Computes the MD5 hex digest of a byte sequence for duplicate file detection.
        """
        return hashlib.md5(file_content).hexdigest()

    @classmethod
    def save_file_to_disk(cls, user_id: int, filename: str, content: bytes) -> Path:
        """
        Writes the uploaded byte payload to the server local upload directory.
        Prefixes the filename with user_id to prevent collision across accounts.
        """
        upload_dir = settings.get_upload_path()
        # Avoid collisions: e.g. "1_document_name.pdf"
        safe_filename = f"{user_id}_{filename.replace(' ', '_')}"
        file_path = upload_dir / safe_filename
        
        with open(file_path, "wb") as f:
            f.write(content)
            
        return file_path

    @classmethod
    def create_document_record(
        cls,
        db: Session,
        user_id: int,
        filename: str,
        filepath: str,
        file_hash: str,
        file_size: int,
        file_type: str
    ) -> Document:
        """
        Creates a new Document metadata entry in the relational database.
        """
        db_doc = Document(
            user_id=user_id,
            filename=filename,
            filepath=filepath,
            file_hash=file_hash,
            file_size=file_size,
            file_type=file_type.lower().strip("."),
            status="processing"
        )
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)
        return db_doc

    @classmethod
    def delete_document(cls, db: Session, doc: Document) -> bool:
        """
        Deletes a document:
        1. Removes the physical file from the server disk.
        2. Deletes the database metadata registry.
        """
        # 1. Delete physical file
        try:
            if os.path.exists(doc.filepath):
                os.remove(doc.filepath)
                logger.info("Deleted physical file from disk", path=doc.filepath)
            else:
                logger.warning("Physical file not found on disk during deletion", path=doc.filepath)
        except OSError as e:
            logger.error("Failed to delete physical file", path=doc.filepath, error=str(e))
            # Continue database deletion so the system doesn't stay out of sync
            
        # 2. Delete vectors from ChromaDB
        from app.rag.vectorstore import VectorStoreManager
        VectorStoreManager.delete_document_vectors(doc_id=doc.id)
            
        # 3. Delete DB record
        try:
            db.delete(doc)
            db.commit()
            logger.info("Deleted document database registry", doc_id=doc.id)
            return True
        except Exception as e:
            logger.error("Failed to delete document from database", doc_id=doc.id, error=str(e))
            db.rollback()
            return False
