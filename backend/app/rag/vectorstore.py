from typing import List
# pyright: ignore [reportMissingImports]
from langchain_chroma import Chroma
from app.core.config import settings
from app.rag.embeddings import get_embeddings_provider
from app.rag.text_splitter import get_text_splitter
from app.core.logging import logger

def get_vectorstore() -> Chroma:
    """
    Initializes and returns a connection instance to the local persistent ChromaDB.
    """
    # Create target directories on initialization
    settings.get_chroma_path()
    
    return Chroma(
        collection_name=settings.CHROMA_COLLECTION_NAME,
        persist_directory=settings.CHROMA_DB_DIR,
        embedding_function=get_embeddings_provider()
    )

class VectorStoreManager:
    """
    Orchestrates ingestion and deletion processes for vector database entries.
    """
    
    @classmethod
    def index_document_text(cls, text: str, doc_id: int, user_id: int, filename: str) -> None:
        """
        Splits raw text, maps security/ownership metadata to each segment,
        and saves the resulting vectors in ChromaDB.
        """
        logger.info(
            "Vector ingestion started...",
            doc_id=doc_id,
            user_id=user_id,
            filename=filename,
            text_length=len(text)
        )
        
        # 1. Chunk the document text
        splitter = get_text_splitter()
        chunks = splitter.split_text(text)
        logger.info("Text split completed", doc_id=doc_id, chunks_count=len(chunks))
        
        # 2. Build metadata mapping for multi-tenancy and citations
        metadatas = []
        for idx, chunk in enumerate(chunks):
            metadatas.append({
                "document_id": doc_id,
                "user_id": user_id,
                "filename": filename,
                "chunk_index": idx
            })
            
        # 3. Add texts to vector database
        vectorstore = get_vectorstore()
        vectorstore.add_texts(texts=chunks, metadatas=metadatas)
        logger.info("Successfully indexed vectors in ChromaDB", doc_id=doc_id, chunks_count=len(chunks))

    @classmethod
    def delete_document_vectors(cls, doc_id: int) -> None:
        """
        Deletes all vector segments associated with a document ID from ChromaDB.
        Queries the document chunks first to get their IDs, then deletes them.
        """
        logger.info("Deleting vectors for document...", doc_id=doc_id)
        vectorstore = get_vectorstore()
        try:
            # 1. Query for matching chunk entries by document_id
            results = vectorstore.get(where={"document_id": doc_id})
            ids = results.get("ids", [])
            
            # 2. Delete the matched IDs from Chroma DB
            if ids:
                vectorstore.delete(ids=ids)
                logger.info("Vectors successfully deleted from ChromaDB", doc_id=doc_id, count=len(ids))
            else:
                logger.info("No vectors found in ChromaDB for document", doc_id=doc_id)
        except Exception as e:
            logger.error("Failed to delete vectors from ChromaDB", doc_id=doc_id, error=str(e))
