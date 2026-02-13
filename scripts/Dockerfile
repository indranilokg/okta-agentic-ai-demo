FROM python:3.11-slim

WORKDIR /scripts

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire project (needed for imports from rag/, auth/, etc.)
COPY ./scripts/clear_pinecone.py .
COPY ./scripts/upload_security_doc.py .
COPY ./rag/ ./rag/
COPY ./auth/ ./auth/

# Default command (can be overridden)
CMD ["python", "upload_security_doc.py"]
