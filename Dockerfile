FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the main script
COPY pdf_structure_extractor.py .

# Create input and output directories
RUN mkdir -p /app/input /app/output

# Set the default command
ENTRYPOINT ["python", "pdf_structure_extractor.py"]

# Metadata
LABEL maintainer="PDF Structure Extractor"
LABEL description="Intelligent PDF structure extraction with multilingual support"
LABEL version="2.0"
