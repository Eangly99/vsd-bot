FROM python:3.11-slim

# Install system dependencies including FFmpeg and Node.js (JS engine for yt-dlp)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    nodejs \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create downloads directory
RUN mkdir -p /app/downloads

# Environment defaults
ENV PYTHONUNBUFFERED=1
ENV DOWNLOAD_DIR=/app/downloads

CMD ["python", "main.py"]
