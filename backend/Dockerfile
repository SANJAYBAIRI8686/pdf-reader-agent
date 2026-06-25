FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Install system dependencies needed for compiling native packages like bcrypt and ChromaDB
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip and install dependency specifications
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend source directory
COPY app app

# Create folders for uploads, sqlite database, and vector storage indices
RUN mkdir -p /app/data /app/uploaded_files /app/chroma_data

# Expose FastAPI port
EXPOSE 8000

# Run uvicorn server binding to 0.0.0.0 for host networking access
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
