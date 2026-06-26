FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/app/.cache/huggingface \
    DATABASE_PATH=/app/data/app.db \
    ADMIN_PASSWORD=admin123 \
    LOCALHOST_RATE_LIMIT=120

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

# Create directory for SQLite database storage
RUN mkdir -p /app/data

# Copy requirements
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose database directory as a volume for data persistence
VOLUME /app/data

# Expose the API port
EXPOSE 8998

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8998"]
