from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.document import DocumentOut, DocumentUploadResponse
from app.services.document_service import DocumentService
from app.services.tasks import parse_and_index_document
from app.core.config import settings

# Initialize the API router for document endpoints
router = APIRouter()

ALLOWED_EXTENSIONS = {"pdf", "docx", "md", "markdown", "txt"}

@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks,
    response: Response  # Inject Response object to allow dynamic status code overrides
) -> Any:
    """
    Upload a document (PDF, DOCX, MD) and process it in the background.
    Automatically detects duplicate uploads based on file content MD5 hash.
    """
    # 1. Validate file extension
    filename = file.filename or "unnamed_file"
    file_ext = filename.split(".")[-1].lower() if "." in filename else ""
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '.{file_ext}'. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}"
        )
        
    # 2. Read content and validate file size
    file_bytes = await file.read()
    file_size = len(file_bytes)
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum upload size of {settings.MAX_UPLOAD_SIZE_MB}MB."
        )

    # 3. Calculate MD5 hash for duplicate detection
    file_hash = DocumentService.calculate_md5(file_bytes)
    
    # Check if this user has already uploaded this file content
    existing_doc = DocumentService.get_document_by_hash(db, user_id=current_user.id, file_hash=file_hash)
    if existing_doc:
        # Override default 201 status code to 200 OK for duplicate detection
        response.status_code = status.HTTP_200_OK
        return {
            "message": "Duplicate document detected. Using existing record.",
            "document": existing_doc,
            "is_duplicate": True
        }

    # 4. Save file to disk
    try:
        file_path = DocumentService.save_file_to_disk(
            user_id=current_user.id,
            filename=filename,
            content=file_bytes
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write file to storage: {str(e)}"
        )

    # 5. Create database record
    doc_record = DocumentService.create_document_record(
        db=db,
        user_id=current_user.id,
        filename=filename,
        filepath=str(file_path),
        file_hash=file_hash,
        file_size=file_size,
        file_type=file_ext
    )

    # 6. Dispatch background task to parse file asynchronously
    background_tasks.add_task(parse_and_index_document, doc_record.id)

    return {
        "message": "Document uploaded successfully. Parsing in progress.",
        "document": doc_record,
        "is_duplicate": False
    }

@router.get("/", response_model=List[DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    List all uploaded documents belonging to the authenticated user.
    """
    documents = DocumentService.get_user_documents(db, user_id=current_user.id)
    return documents

@router.get("/{doc_id}", response_model=DocumentOut)
def get_document_status(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Fetch the details/processing status of a specific document.
    """
    doc = DocumentService.get_document_by_id(db, doc_id=doc_id)
    if not doc or doc.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )
    return doc

@router.delete("/{doc_id}")
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Deletes a document from server storage and database indices.
    """
    doc = DocumentService.get_document_by_id(db, doc_id=doc_id)
    if not doc or doc.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )
        
    success = DocumentService.delete_document(db, doc=doc)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document from backend index."
        )
        
    return {"message": "Document deleted successfully."}
