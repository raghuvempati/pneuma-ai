# Use the official Python 3.12 slim image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

# Create and set the working directory
WORKDIR /app

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- NEW: Download the Spacy NLP Model for Presidio ---
RUN python -m spacy download en_core_web_sm

# Copy the actual application source code
COPY src/ ./src/

# Expose the API port
EXPOSE 8000

# Start the Uvicorn server
CMD ["uvicorn", "pneuma.api.server:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]