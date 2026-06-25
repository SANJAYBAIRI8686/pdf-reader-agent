from typing import Dict, List, Any
# pyright: ignore [reportMissingImports]
from langchain_core.prompts import ChatPromptTemplate
# pyright: ignore [reportMissingImports]
from langchain_core.runnables import RunnablePassthrough
# pyright: ignore [reportMissingImports]
from langchain_core.output_parsers import StrOutputParser
# pyright: ignore [reportMissingImports]
from langchain_openai import ChatOpenAI
from app.core.config import settings
from app.rag.vectorstore import get_vectorstore
from app.core.logging import logger

def get_retriever(user_id: int) -> Any:
    """
    Returns a vector store retriever filtered by user_id to enforce multi-tenancy.
    """
    vectorstore = get_vectorstore()
    return vectorstore.as_retriever(
        search_kwargs={
            "filter": {"user_id": user_id},
            "k": 4
        }
    )

def format_docs(docs: List[Any]) -> str:
    """
    Formats list of retrieved LangChain Document objects into a plain text
    context block with explicit file name markers.
    """
    formatted_chunks = []
    for doc in docs:
        filename = doc.metadata.get("filename", "unknown_source")
        formatted_chunks.append(f"--- Document Source: {filename} ---\n{doc.page_content}")
    return "\n\n".join(formatted_chunks)

class RAGEngine:
    """
    Core RAG orchestrator running queries against ChromaDB and OpenAI.
    """
    
    @classmethod
    def query(cls, query_text: str, user_id: int) -> Dict[str, Any]:
        """
        Executes a RAG query:
        1. Retrieves semantic matches belonging to user_id.
        2. Formats context.
        3. Prompts the LLM (or returns a mock check if offline).
        4. Isolates and returns sources citations.
        """
        logger.info("Executing RAG query...", user_id=user_id, query=query_text)
        
        # 1. Fetch relevant document chunks
        retriever = get_retriever(user_id=user_id)
        matched_docs = retriever.invoke(query_text)
        
        # Extract cited sources list
        citations = []
        seen_sources = set()
        for doc in matched_docs:
            filename = doc.metadata.get("filename", "unknown")
            doc_id = doc.metadata.get("document_id", None)
            chunk_idx = doc.metadata.get("chunk_index", None)
            
            source_key = (filename, doc_id)
            if source_key not in seen_sources:
                seen_sources.add(source_key)
                citations.append({
                    "filename": filename,
                    "document_id": doc_id,
                    "chunk_index": chunk_idx
                })
                
        # 2. Check if we are running in local offline test mode
        is_placeholder_key = (
            not settings.OPENAI_API_KEY 
            or "your-openai-api-key" in settings.OPENAI_API_KEY.lower()
            or settings.OPENAI_API_KEY == "mock-key"
        )
        
        if is_placeholder_key:
            logger.info("Running query in offline mock mode")
            # Build intelligent mock response based on matched documents
            if not matched_docs:
                mock_answer = "I cannot find any relevant information in the uploaded documents to answer your question."
            else:
                sources_str = ", ".join([f"'{c['filename']}'" for c in citations])
                mock_answer = (
                    f"[Mock Offline Mode] I searched your documents and found {len(matched_docs)} "
                    f"relevant paragraphs in {sources_str}. Here is a mock retrieval answer for your question: '{query_text}'."
                )
            return {
                "answer": mock_answer,
                "citations": citations,
                "offline_mode": True
            }

        # 3. Configure real LangChain Chain (when valid key is present)
        try:
            llm = ChatOpenAI(
                model=settings.LLM_MODEL,
                openai_api_key=settings.OPENAI_API_KEY,
                temperature=0.0
            )
            
            prompt = ChatPromptTemplate.from_template("""
You are an AI Research Assistant. Answer the user's question based strictly on the provided context.
If you cannot find the answer, state that you cannot find it in the uploaded documents. Do not make up answers.
For every fact you state, you must cite the source filename (e.g., [source: filename.pdf]).

Context:
{context}

Question: {question}
Answer:""")

            # Construct LCEL pipeline
            chain = (
                {"context": lambda x: format_docs(matched_docs), "question": RunnablePassthrough()}
                | prompt
                | llm
                | StrOutputParser()
            )
            
            answer = chain.invoke(query_text)
            
            return {
                "answer": answer,
                "citations": citations,
                "offline_mode": False
            }
        except Exception as e:
            logger.error("Failed to execute LLM prompt chain", error=str(e))
            raise HTTPException(
                status_code=500,
                detail=f"Failed to query LLM provider: {str(e)}"
            )
