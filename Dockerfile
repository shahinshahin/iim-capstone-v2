# Use a lightweight Python image
FROM python:3.10-slim

# Set environment variables for performance and logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TRANSFORMERS_CACHE=/app/hf_cache \
    HF_HOME=/app/hf_cache

# Set working directory
WORKDIR /app

# Install system dependencies for pandas, openpyxl, and model loading
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    gcc \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create essential directories
RUN mkdir -p /app/outputs /app/templates /app/hf_cache

# Copy application files
COPY . .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Expose the port used by FastAPI
EXPOSE 8000

# Run the FastAPI app using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
