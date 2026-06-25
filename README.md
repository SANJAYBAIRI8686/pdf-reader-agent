# AI Research Assistant

A production-grade, multi-tenant AI Research Assistant built using **FastAPI (Python)**, **React + TypeScript**, **SQLAlchemy + SQLite**, **LangChain**, and **ChromaDB**. 

The application enables users to upload document formats (PDF, DOCX, MD), indexes them securely in a multi-tenant vector database, and supports real-time, event-streamed conversational questions with precise source citations.

---

## Technical Stack & Architecture

### Backend (API)
*   **FastAPI**: Highly performant, asynchronous ASGI web framework.
*   **SQLAlchemy / SQLite**: Relational database engine mapping authentication schemas, chat logs, and document ingestion models.
*   **LangChain**: RAG framework managing text chunk recursive splits and prompting logic.
*   **ChromaDB**: Native vector storage engine using persistent disk indices.
*   **Structlog**: Structured logger tracking security check parameters and execution times.

### Frontend (Client)
*   **React 19 & TypeScript**: Component-driven architecture using modern hooks and context APIs.
*   **Vite**: Next-generation bundler for near-instant hot modular reloading.
*   **Tailwind CSS v4**: High-fidelity UI styles featuring a modern neon dark-theme grid, glowing glassmorphic elements, and responsive slide layouts.
*   **Lucide React**: Clean vector icon components.

---

## Repository Structure

```text
├── backend/
│   ├── app/                      # Python backend code
│   │   ├── api/                  # Authentication, document management, and chat routers
│   │   ├── core/                 # Configs settings, security parameters, and logging hooks
│   │   ├── database/             # SQLite session configurations
│   │   ├── models/               # SQLAlchemy schema definitions
│   │   ├── rag/                  # Parser loaders, embeddings provider factory, Chroma clients
│   │   ├── schemas/              # Pydantic validation structures
│   │   └── services/             # Core business service logic and background indexing workers
│   ├── Dockerfile                # Backend packaging
│   ├── requirements.txt          # Python package locks
│   └── test_*.py                 # Automated integration suites (Auth, Docs, Vectorstore, Chat)
│
├── frontend/
│   ├── src/
│   │   ├── contexts/             # AuthContext routing guards
│   │   ├── pages/                # Login, Register, Dashboard views
│   │   └── services/             # Fetch wrappers and custom async EventStream reader
│   ├── Dockerfile                # Multi-stage production client compiler
│   ├── nginx.conf                # Nginx proxy mapping static files and SSE buffering rules
│   └── package.json              # Client package dependencies
│
└── docker-compose.yml            # Multi-service container orchestrator
```

---

## Getting Started

### Prerequisites
*   [Docker](https://www.docker.com/) and Docker Compose installed.
*   An OpenAI API key (for embedding extraction and generation).

### Configuration Setup
Create a `.env` file at the **root** of the project directory to supply the required secrets:

```env
# RAG Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Security Configurations
JWT_SECRET=generate_a_secure_random_string_here
```

---

## Deployment: Running with Docker Compose

To build and spin up the complete containerized stack:

```bash
docker compose up --build -d
```

*   The **React Client** will be accessible at: **`http://localhost`** (port 80).
*   The **FastAPI Swagger Docs** will be accessible at: **`http://localhost:8000/docs`**.

### Verify Container Health
Check the container statuses and inspect current output logs:

```bash
docker compose ps
docker compose logs -f
```

To shut down and wipe the containers:

```bash
docker compose down
```

*Note: In Docker Compose, local backend volume maps (`./backend/data`, `./backend/uploaded_files`, `./backend/chroma_data`) are mounted dynamically, ensuring that all databases, document assets, and indexed vectors survive image rebuilds and service restarts.*

---

## Local Development Setup

If you prefer to run the applications locally without Docker:

### 1. Backend API Setup
1.  Navigate into the `backend/` directory:
    ```bash
    cd backend
    ```
2.  Create a virtual environment and activate it:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```
3.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Configure your environment parameters inside `backend/.env` (use `backend/.env.example` as a template).
5.  Start the FastAPI hot-reload server:
    ```bash
    uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
    ```

### 2. Frontend Client Setup
1.  Navigate into the `frontend/` directory:
    ```bash
    cd ../frontend
    ```
2.  Install the package dependencies:
    ```bash
    npm install
    ```
3.  Launch the Vite developer client:
    ```bash
    npm run dev
    ```
4.  Open the web app in your browser at the indicated Vite port (usually **`http://localhost:5173`**).

---

## Running Automated Backend Tests

We have written comprehensive integration tests to verify database configurations, session workflows, token streams, and multi-tenant security structures.

To execute the test suite locally:

1.  Make sure you are in the `backend/` directory with your virtual environment active.
2.  Run the tests using Python:

```bash
# 1. Verify basic SQLite connection setup
python test_infra.py

# 2. Verify registration, token generation, and routing gates
python test_auth.py

# 3. Verify PDF/Word/Markdown parsers and duplicate file overrides
python test_docs.py

# 4. Verify user-isolated vector ingestion
python test_rag.py

# 5. Verify Server-Sent Events (SSE) token streaming and semantic searches
python test_chat.py
```

*Note: If no valid OpenAI API key is supplied, the test suite fallback configuration invokes a mock vector indexer (`FakeEmbeddings`), allowing you to execute all integration check routines offline without incurring API costs.*
