import os
import sys
import json
from pathlib import Path
from fastapi.testclient import TestClient

# Mute Chroma anonymous telemetry warnings in tests
os.environ["ANONYMOUS_TELEMETRY"] = "False"

# Add current path to python search path
sys.path.append(str(Path(__file__).resolve().parent))

from app.main import app
from app.database.session import SessionLocal
from app.models.user import User
from app.rag.vectorstore import VectorStoreManager

client = TestClient(app)

def test_chat_and_streaming_workflow():
    print("\n=== STARTING CHAT & STREAMING SUITE TESTS ===")
    
    test_email = "chat_junior_dev_tester@example.com"
    test_password = "SecurePassword123!"
    test_name = "Junior Chat Tester"
    
    # 1. Pre-test cleanup: ensure database is clean of this user
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.email == test_email).first()
        if existing_user:
            db.delete(existing_user)
            db.commit()
    finally:
        db.close()

    # 2. Register & Login to get token
    client.post(
        "/api/v1/auth/register",
        json={"email": test_email, "password": test_password, "full_name": test_name}
    )
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": test_email, "password": test_password}
    )
    login_json = login_response.json()
    token = login_json["access_token"]
    user_id = 1  # Standard auto-increment start, but we can read it dynamically from /me
    
    me_response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = me_response.json()["id"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 3. Create dummy context documents in vectorstore
    print("Seeding dummy RAG vector context for user...")
    doc_id = 999
    doc_text = "Standard guidelines on Agentic Workflows. Antigravity AI is a state-of-the-art coding assistant."
    VectorStoreManager.index_document_text(
        text=doc_text,
        doc_id=doc_id,
        user_id=user_id,
        filename="antigravity_guide.md"
    )

    # 4. Test Chat Session Creation
    print("Testing session creation (POST /api/v1/chat/sessions)...")
    session_response = client.post(
        "/api/v1/chat/sessions",
        json={"title": "New Chat"},
        headers=auth_headers
    )
    assert session_response.status_code == 201
    session_json = session_response.json()
    session_id = session_json["id"]
    assert session_json["title"] == "New Chat"
    print("✓ Session creation passed.")

    # 5. Test SSE Streaming Query Endpoint
    print("Testing Server-Sent Events (SSE) streaming query...")
    query_payload = {"content": "What is Antigravity AI?"}
    
    # Establish a streaming connection
    stream_res = client.post(
        f"/api/v1/chat/sessions/{session_id}/query",
        json=query_payload,
        headers=auth_headers
    )
    assert stream_res.status_code == 200
    assert "text/event-stream" in stream_res.headers["content-type"]
    
    has_citations = False
    tokens_received = []
    is_done = False
    
    for line in stream_res.iter_lines():
        if not line:
            continue
        line = line.strip()
        if not line.startswith("data:"):
            continue
            
        data_content = line[5:].strip()
        
        if data_content == "[DONE]":
            is_done = True
            continue
            
        data = json.loads(data_content)
        
        # Check for initial citations payload
        if "citations" in data:
            has_citations = True
            assert len(data["citations"]) > 0
            assert data["citations"][0]["filename"] == "antigravity_guide.md"
            print("✓ Stream yielded initial source citations payload.")
            
        # Accumulate text tokens
        if "token" in data:
            tokens_received.append(data["token"])
            
    # Assert full streaming cycle
    assert has_citations
    assert len(tokens_received) > 0
    assert is_done
    full_text = "".join(tokens_received)
    assert "[Mock Answer]" in full_text or "Antigravity" in full_text
    print("✓ Response streamed token-by-token successfully.")

    # 6. Test Message History Listing
    print("Testing message history listing (GET /api/v1/chat/sessions/{id}/messages)...")
    history_res = client.get(f"/api/v1/chat/sessions/{session_id}/messages", headers=auth_headers)
    assert history_res.status_code == 200
    history_json = history_res.json()
    
    # User prompt + assistant answer = 2 messages
    assert len(history_json) == 2
    assert history_json[0]["role"] == "user"
    assert history_json[1]["role"] == "assistant"
    assert len(history_json[1]["citations"]) > 0
    assert history_json[1]["citations"][0]["filename"] == "antigravity_guide.md"
    print("✓ Message history listing verification passed.")

    # 7. Verify Dynamic Renaming
    print("Verifying dynamic session title renaming...")
    session_status = client.get("/api/v1/chat/sessions", headers=auth_headers)
    active_sessions = session_status.json()
    # The session title should have been renamed from "New Chat" to the first user question
    assert active_sessions[0]["id"] == session_id
    assert active_sessions[0]["title"] != "New Chat"
    print(f"✓ Dynamic renaming passed. Current Title: {active_sessions[0]['title']}")

    # 8. Test Standalone Semantic Search
    print("Testing standalone semantic search (GET /api/v1/chat/search)...")
    search_res = client.get("/api/v1/chat/search?q=coding+assistant", headers=auth_headers)
    assert search_res.status_code == 200
    search_hits = search_res.json()
    assert len(search_hits) > 0
    assert search_hits[0]["filename"] == "antigravity_guide.md"
    print("✓ Standalone semantic search retrieval passed.")

    # 9. Test Session Deletion
    print("Testing chat session deletion (DELETE /api/v1/chat/sessions/{id})...")
    del_res = client.delete(f"/api/v1/chat/sessions/{session_id}", headers=auth_headers)
    assert del_res.status_code == 200
    
    # Assert messages and session are removed (should return 404 now)
    gone_res = client.get(f"/api/v1/chat/sessions/{session_id}/messages", headers=auth_headers)
    assert gone_res.status_code == 404
    print("✓ Cascaded session deletion passed.")

    # 10. Tear Down test data
    print("Running final test databases cleanup...")
    VectorStoreManager.delete_document_vectors(doc_id=doc_id)
    db = SessionLocal()
    try:
        user_record = db.query(User).filter(User.email == test_email).first()
        if user_record:
            db.delete(user_record)
            db.commit()
            print("✓ Database cleaned successfully.")
    except Exception as e:
        print(f"Cleanup failed: {e}")
        db.rollback()
    finally:
        db.close()
        
    print("=== ALL CHAT & STREAMING SUITE TESTS PASSED SUCCESSFULLY ===\n")

if __name__ == "__main__":
    test_chat_and_streaming_workflow()
