FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only OSP source code (NOT ai_core — it is in .gitignore and .dockerignore)
COPY osp_server ./osp_server
COPY osp_core ./osp_core
COPY osp_std ./osp_std
COPY skills ./skills

# Set Python path to include current directory
ENV PYTHONPATH=/app

# Expose OSP server port
EXPOSE 8000

# Run the OSP Reference Server (not dashboard)
# Set OSP_ADMIN_KEY via environment variable before running
CMD ["uvicorn", "osp_server.server:app", "--host", "0.0.0.0", "--port", "8000"]
