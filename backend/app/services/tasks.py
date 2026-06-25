import re
from collections import Counter
from app.database.session import SessionLocal
from app.services.document_service import DocumentService
from app.rag.parser import DocumentParser
from app.core.logging import logger

def parse_and_index_document(doc_id: int) -> None:
    """
    Background worker task that:
    1. Loads the document from SQLite.
    2. Parses its text depending on the extension (PDF, DOCX, MD).
    3. Generates a summary stub and extracts keywords.
    4. In Phase 4, it will generate vector embeddings and load them into ChromaDB.
    5. Updates the document status to 'processed' or 'failed'.
    """
    logger.info("Background document parsing started", doc_id=doc_id)
    
    # Establish a separate connection context for the background thread
    db = SessionLocal()
    try:
        doc = DocumentService.get_document_by_id(db, doc_id=doc_id)
        if not doc:
            logger.error("Document not found in database for background processing", doc_id=doc_id)
            return

        # 1. Parse text from physical disk file
        extracted_text = DocumentParser.extract_text(
            file_path=doc.filepath,
            file_type=doc.file_type
        )
        
        if not extracted_text.strip():
            raise ValueError("Extracted text content is empty.")
            
        # 2. Extract keywords using standard word frequency checks
        words = re.findall(r"\b[a-zA-Z]{5,15}\b", extracted_text.lower())
        stopwords = {
            "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
            "arent", "as", "at", "be", "because", "been", "before", "being", "below", "between",
            "both", "but", "by", "cant", "cannot", "could", "couldnt", "did", "didnt", "do", "does",
            "doesnt", "doing", "dont", "down", "during", "each", "few", "for", "from", "further",
            "had", "hadnt", "has", "hasnt", "have", "havent", "having", "he", "hed", "hell", "hes",
            "her", "here", "heres", "hers", "herself", "him", "himself", "his", "how", "hows",
            "i", "id", "ill", "im", "ive", "if", "in", "into", "is", "isnt", "it", "its", "itself",
            "lets", "me", "more", "most", "mustnt", "my", "myself", "no", "nor", "not", "of", "off",
            "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over",
            "own", "same", "shant", "she", "shed", "shell", "shes", "should", "shouldnt", "so", "some",
            "such", "than", "that", "thats", "the", "their", "theirs", "them", "themselves", "then",
            "there", "theres", "these", "they", "theyd", "theyll", "theyre", "theyve", "this", "those",
            "through", "to", "too", "under", "until", "up", "very", "was", "wasnt", "we", "wed", "well",
            "were", "weve", "werent", "what", "whats", "when", "whens", "where", "wheres", "which",
            "while", "who", "whos", "whom", "why", "whys", "with", "wont", "would", "wouldnt", "you",
            "youd", "youll", "youre", "youve", "your", "yours", "yourself", "yourselves", "would"
        }
        
        filtered_words = [w for w in words if w not in stopwords]
        word_counts = Counter(filtered_words)
        # Select top 5 most frequent descriptive keywords
        top_keywords = [k for k, v in word_counts.most_common(5)]
        doc.keywords = ", ".join(top_keywords)
        
        # 3. Generate Summary stub
        # Clean double spacing/newlines for display
        cleaned_text = re.sub(r"\s+", " ", extracted_text).strip()
        summary_limit = 200
        if len(cleaned_text) > summary_limit:
            doc.summary = f"{cleaned_text[:summary_limit]}..."
        else:
            doc.summary = cleaned_text
            
        # 4. Mark status as processed
        doc.status = "processed"
        db.add(doc)
        db.commit()
        logger.info("Background document parsing succeeded", doc_id=doc.id, keywords=doc.keywords)
        
    except Exception as e:
        logger.error("Background document parsing failed", doc_id=doc_id, error=str(e))
        # Safely attempt to mark status as failed in database
        try:
            doc = DocumentService.get_document_by_id(db, doc_id=doc_id)
            if doc:
                doc.status = "failed"
                db.add(doc)
                db.commit()
        except Exception as db_err:
            logger.error("Failed to update status to failed during exception handling", doc_id=doc_id, error=str(db_err))
            db.rollback()
    finally:
        db.close()
