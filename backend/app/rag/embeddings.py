from langchain_core.embeddings import Embeddings
# pyright: ignore [reportMissingImports]
from langchain_openai import OpenAIEmbeddings
# pyright: ignore [reportMissingImports]
from langchain_community.embeddings import OllamaEmbeddings
# pyright: ignore [reportMissingImports]
from langchain_core.embeddings.fake import FakeEmbeddings
from app.core.config import settings
from app.core.logging import logger

def get_embeddings_provider() -> Embeddings:
    """
    Returns the configured LangChain Embeddings provider.
    Falls back to FakeEmbeddings if the OpenAI API Key is the default placeholder,
    enabling offline development and zero-cost local tests.
    """
    # Check if we are running in local test mode without a real OpenAI key
    is_placeholder_key = (
        not settings.OPENAI_API_KEY 
        or "your-openai-api-key" in settings.OPENAI_API_KEY.lower()
        or settings.OPENAI_API_KEY == "mock-key"
    )
    
    if is_placeholder_key:
        logger.info("Using offline FakeEmbeddings for development/testing (no valid OpenAI key set)")
        # size=1536 matches standard text-embedding-3-small/text-embedding-ada-002 dimensions
        return FakeEmbeddings(size=1536)
        
    provider = settings.LLM_PROVIDER.lower().strip()
    
    if provider == "openai":
        logger.info("Initializing OpenAI Embeddings provider", model=settings.EMBEDDING_MODEL)
        return OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY
        )
    elif provider == "ollama":
        logger.info("Initializing Ollama Embeddings provider", model=settings.EMBEDDING_MODEL)
        # Assumes Ollama is running locally
        return OllamaEmbeddings(
            model=settings.EMBEDDING_MODEL
        )
    else:
        logger.warning(
            "Unknown embeddings provider configured. Falling back to FakeEmbeddings.",
            provider=provider
        )
        return FakeEmbeddings(size=1536)
