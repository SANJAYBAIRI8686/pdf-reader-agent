import json
import asyncio
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.chat import ChatSessionOut, ChatSessionCreate, ChatMessageOut, ChatMessageCreate, SemanticSearchHit
from app.services.chat_service import ChatService
from app.rag.engine import get_retriever, format_docs
from app.rag.vectorstore import get_vectorstore
from app.core.config import settings
from app.core.logging import logger

# pyright: ignore [reportMissingImports]
from langchain_core.prompts import ChatPromptTemplate
# pyright: ignore [reportMissingImports]
from langchain_openai import ChatOpenAI

# Initialize the API router for chat endpoints
router = APIRouter()

@router.post("/sessions", response_model=ChatSessionOut, status_code=status.HTTP_201_CREATED)
def create_chat_session(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    session_in: ChatSessionCreate
) -> Any:
    """
    Start a new conversational chat session.
    """
    title = session_in.title.strip() if session_in.title else None
    session = ChatService.create_session(db, user_id=current_user.id, title=title)
    return session

@router.get("/sessions", response_model=List[ChatSessionOut])
def list_chat_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    List all chat sessions belonging to the authenticated user.
    """
    sessions = ChatService.get_user_sessions(db, user_id=current_user.id)
    return sessions

@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageOut])
def list_session_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Retrieve message history logs for a specific session.
    """
    session = ChatService.get_session(db, session_id=session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found."
        )
    messages = ChatService.get_session_messages(db, session_id=session_id)
    return messages

@router.delete("/sessions/{session_id}")
def delete_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Delete a chat session and all its message history.
    """
    session = ChatService.get_session(db, session_id=session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found."
        )
    success = ChatService.delete_session(db, session=session)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete chat session."
        )
    return {"message": "Chat session deleted successfully."}

@router.post("/sessions/{session_id}/query")
async def query_chat_session_stream(
    session_id: int,
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    query_in: ChatMessageCreate
) -> Any:
    """
    Queries the RAG engine for a session and streams back the response
    token-by-token using Server-Sent Events (SSE).
    """
    # 1. Verify session ownership
    session = ChatService.get_session(db, session_id=session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found."
        )

    # 2. Update session title from first prompt if title is default
    user_prompt = query_in.content.strip()
    if session.title == "New Chat":
        new_title = user_prompt[:40] + "..." if len(user_prompt) > 40 else user_prompt
        ChatService.update_session_title(db, session=session, new_title=new_title)

    # 3. Log user prompt in relational DB
    ChatService.create_message(
        db, session_id=session_id, role="user", content=user_prompt
    )

    # 4. Fetch context from vector DB
    retriever = get_retriever(user_id=current_user.id)
    matched_docs = retriever.invoke(user_prompt)

    # Compile citation lists
    citations = []
    seen = set()
    for doc in matched_docs:
        filename = doc.metadata.get("filename", "unknown")
        doc_id = doc.metadata.get("document_id")
        chunk_idx = doc.metadata.get("chunk_index")
        
        source_key = (filename, doc_id)
        if source_key not in seen:
            seen.add(source_key)
            citations.append({
                "filename": filename,
                "document_id": doc_id,
                "chunk_index": chunk_idx
            })

    # 5. Define streaming generator
    async def event_stream_generator():
        # First: Yield cited documents so React can render source icons instantly
        yield f"data: {json.dumps({'citations': citations})}\n\n"
        await asyncio.sleep(0.01)
        
        # Check if we should fallback to offline simulation mode
        is_placeholder_key = (
            not settings.OPENAI_API_KEY 
            or "your-openai-api-key" in settings.OPENAI_API_KEY.lower()
            or settings.OPENAI_API_KEY == "mock-key"
        )
        
        if is_placeholder_key:
            sources_str = ", ".join([f"'{c['filename']}'" for c in citations]) if citations else "no documents"
            mock_answer = (
                f"[Mock Answer] I retrieved {len(matched_docs)} text segments from your files "
                f"({sources_str}) to answer your query. "
                f"Here is a mock response details for: '{user_prompt}'."
            )
            
            accumulated = ""
            for char in mock_answer:
                accumulated += char
                yield f"data: {json.dumps({'token': char})}\n\n"
                await asyncio.sleep(0.005) # Typist delay
                
            # Log final answer + citations context to message history table
            ChatService.create_message(
                db, session_id=session_id, role="assistant", content=mock_answer, citations=citations
            )
            yield "data: [DONE]\n\n"
            
        else:
            try:
                llm = ChatOpenAI(
                    model=settings.LLM_MODEL,
                    openai_api_key=settings.OPENAI_API_KEY,
                    temperature=0.0,
                    streaming=True
                )
                
                prompt_template = ChatPromptTemplate.from_template("""
You are an AI Research Assistant. Answer the user's question based strictly on the provided context.
If you cannot find the answer, state that you cannot find it in the uploaded documents. Do not make up answers.
For every fact you state, you must cite the source filename (e.g., [source: filename.pdf]).

Context:
{context}

Question: {question}
Answer:""")

                context_block = format_docs(matched_docs)
                formatted_prompt = prompt_template.format(
                    context=context_block,
                    question=user_prompt
                )
                
                accumulated_text = ""
                # Stream token generator using LangChain astream
                async for chunk in llm.astream(formatted_prompt):
                    token = chunk.content
                    accumulated_text += token
                    yield f"data: {json.dumps({'token': token})}\n\n"
                    
                # Save complete log to database
                ChatService.create_message(
                    db, session_id=session_id, role="assistant", content=accumulated_text, citations=citations
                )
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error("Streaming prompt query failed", error=str(e))
                # Stream error payload
                yield f"data: {json.dumps({'error': f'Failed to generate response: {str(e)}'})}\n\n"
                yield "data: [DONE]\n\n"

    # Return standard event-stream headers
    return StreamingResponse(
        event_stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Encoding": "none"
        }
    )

@router.get("/search", response_model=List[SemanticSearchHit])
def semantic_search(
    q: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Standalone semantic vector search.
    Searches ChromaDB matching the user_id context.
    """
    if not q.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query string cannot be empty."
        )
        
    vectorstore = get_vectorstore()
    try:
        # Chroma similarity search returning document and distance metric
        raw_results = vectorstore.similarity_search_with_score(
            query=q,
            k=5,
            filter={"user_id": current_user.id}
        )
        
        search_hits = []
        for doc, score in raw_results:
            search_hits.append({
                "text": doc.page_content,
                "filename": doc.metadata.get("filename", "unknown"),
                "document_id": doc.metadata.get("document_id", 0),
                "score": float(score)  # Convert float32 score
            })
            
        return search_hits
    except Exception as e:
        logger.error("Semantic search query failed", query=q, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic search failed: {str(e)}"
        )
