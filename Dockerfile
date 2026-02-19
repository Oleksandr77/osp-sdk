FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (needed for ChromaDB/swig/etc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements (we will create this next)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY osp_server ./osp_server
COPY osp_core ./osp_core
COPY osp_std ./osp_std
COPY ai_core ./ai_core
COPY skills ./skills
COPY dashboard ./dashboard

# Set Python path to include current directory
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Run the dashboard
CMD ["uvicorn", "dashboard.main:app", "--host", "0.0.0.0", "--port", "8000"]
