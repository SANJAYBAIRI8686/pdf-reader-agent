import os
import sys

# Mute Chroma anonymous telemetry warnings in tests
os.environ["ANONYMOUS_TELEMETRY"] = "False"

# Add current path to python search path
sys.path.append(str(Path(__file__).resolve().parent) if "Path" in globals() else os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.rag.text_splitter import get_text_splitter
from app.rag.vectorstore import VectorStoreManager, get_vectorstore
from app.rag.engine import RAGEngine

def test_rag_pipeline():
    print("\n=== STARTING RAG PIPELINE & MULTI-TENANCY TESTS ===")
    
    # 1. Verify Text Splitter
    print("Testing text splitter...")
    splitter = get_text_splitter(chunk_size=100, chunk_overlap=20)
    sample_text = (
        "FastAPI is a modern, fast (high-performance), web framework for building APIs with Python. "
        "It is based on standard Python type hints and is designed to be easy to learn and write."
    )
    chunks = splitter.split_text(sample_text)
    assert len(chunks) > 1, f"Splitting failed: only got {len(chunks)} chunks"
    print(f"✓ Splitter test passed. Text chunked into {len(chunks)} segments.")

    # 2. Setup database/Chroma directory targets
    # (Since we are using FakeEmbeddings, this will run cleanly offline)
    vectorstore = get_vectorstore()
    
    # Test users configuration
    user1_id = 101
    user2_id = 102
    
    doc1_id = 901
    doc2_id = 902
    
    user1_text = (
        "The lifecycle of bananas. Bananas are cultivated in tropical regions. "
        "A banana plant takes about nine to twelve months to produce fruit after planting. "
        "They are harvested green and ripened using ethylene gas in local warehouses."
    )
    
    user2_text = (
        "Quantum computing fundamentals. Qubits are the primary units of quantum information. "
        "Unlike classical bits which represent 0 or 1, qubits utilize superposition and entanglement "
        "to perform computations in parallel states."
    )

    try:
        # 3. Index documents for User 1 and User 2
        print("Indexing Document 1 for User 101 (Topic: Bananas)...")
        VectorStoreManager.index_document_text(
            text=user1_text,
            doc_id=doc1_id,
            user_id=user1_id,
            filename="banana_report.txt"
        )

        print("Indexing Document 2 for User 102 (Topic: Quantum Computing)...")
        VectorStoreManager.index_document_text(
            text=user2_text,
            doc_id=doc2_id,
            user_id=user2_id,
            filename="quantum_notes.md"
        )
        
        # 4. Test Multi-tenant Isolation Retrieval
        print("\nVerifying multi-tenant isolation...")
        
        # Query User 1 about Bananas (Should return User 1's report, and NEVER User 2's notes)
        print("Querying User 101 about 'tropical fruit'...")
        q1_res = RAGEngine.query("Where do bananas grow?", user_id=user1_id)
        assert len(q1_res["citations"]) > 0
        filenames1 = [c["filename"] for c in q1_res["citations"]]
        assert "banana_report.txt" in filenames1
        assert "quantum_notes.md" not in filenames1
        print("✓ User 101 queried bananas and retrieved only owned document.")

        # Query User 1 about Qubits (Since User 1 only owns bananas, it should return bananas, and NEVER quantum_notes.md)
        print("Querying User 101 about 'qubits'...")
        q2_res = RAGEngine.query("How do qubits work?", user_id=user1_id)
        filenames2 = [c["filename"] for c in q2_res["citations"]]
        assert "quantum_notes.md" not in filenames2  # Crucial security assertion!
        print("✓ User 101 query isolation passed (User 101 blocked from accessing User 102's data).")

        # Query User 2 about Quantum Computing (Should return User 2's notes, and NEVER User 1's report)
        print("Querying User 102 about 'qubits'...")
        q3_res = RAGEngine.query("Tell me about superposition.", user_id=user2_id)
        assert len(q3_res["citations"]) > 0
        filenames3 = [c["filename"] for c in q3_res["citations"]]
        assert "quantum_notes.md" in filenames3
        assert "banana_report.txt" not in filenames3
        print("✓ User 102 queried quantum and retrieved only owned document.")

        # Query User 2 about Bananas (Should return quantum_notes.md or empty, but NEVER banana_report.txt)
        print("Querying User 102 about 'bananas lifecycle'...")
        q4_res = RAGEngine.query("How do bananas ripen?", user_id=user2_id)
        filenames4 = [c["filename"] for c in q4_res["citations"]]
        assert "banana_report.txt" not in filenames4  # Crucial security assertion!
        print("✓ User 102 query isolation passed (User 102 blocked from accessing User 101's data).")

        # 5. Test vector deletions
        print("\nTesting vector deletion...")
        print("Deleting vectors for Document 1 (User 101)...")
        VectorStoreManager.delete_document_vectors(doc_id=doc1_id)
        
        # Query User 1 about Bananas again (Should now return 0 citations)
        print("Querying User 101 post-deletion...")
        q5_res = RAGEngine.query("Where do bananas grow?", user_id=user1_id)
        assert len(q5_res["citations"]) == 0
        print("✓ Vectors deleted cleanly. Post-delete retrieval is empty.")

    finally:
        # Tear down: Delete remainders
        print("Cleaning remaining test vectors...")
        VectorStoreManager.delete_document_vectors(doc_id=doc2_id)
        print("✓ Cleaned remaining vectors.")
        
    print("=== ALL RAG & MULTI-TENANCY SUITE TESTS PASSED SUCCESSFULLY ===\n")

if __name__ == "__main__":
    test_rag_pipeline()
