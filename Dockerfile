FROM python:3.11-slim

# Define labels
LABEL maintainer="IA Analisadora Team"
LABEL description="Cérebro da Transparência API Backend"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    poppler-utils \
    libpoppler-cpp-dev \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model se houver
RUN python -m spacy download pt_core_news_lg || echo "SpaCy model download failed, continuing"

# Copy application code (including API, CORE, UTILS)
COPY core/ ./core/
COPY utils/ ./utils/
COPY api/ ./api/
COPY main.py .
COPY README.md .

# Create necessary directories
RUN mkdir -p data/reports data/exports data/conhecimento logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/app/data
ENV REPORTS_DIR=/app/data/reports
ENV KNOWLEDGE_DB=/app/data/conhecimento
ENV USE_REDIS=true
ENV PYTHON_PATH=/app

# Expose port for FastAPI
EXPOSE 8000

# Default command for API deployment
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
