FROM --platform=linux/amd64 python:3.11-slim

# Set working directory
WORKDIR /app

# Install minimal system dependencies for AMD64
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the main extraction script
COPY pdf_structure_extractor.py .

# Create input and output directories
RUN mkdir -p /app/input /app/output

# Set the default command to process all PDFs automatically
CMD ["python", "pdf_structure_extractor.py"]

# Metadata labels
LABEL maintainer="PDF Structure Extractor"
LABEL description="Offline PDF structure extraction with multilingual support"
LABEL version="2.0"
LABEL architecture="amd64"
LABEL constraints="≤200MB memory, ≤10s runtime, ≤50 pages, offline processing"