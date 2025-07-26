#!/bin/bash

# Build the Docker image
echo "Building PDF Structure Extractor Docker image..."
docker build -t pdf-extractor .

# Create directories for testing
mkdir -p input output

echo "Docker image built successfully!"
echo ""
echo "Usage:"
echo "1. Place your PDF files in the 'input' directory"
echo "2. Run: docker run -v \$(pwd)/input:/app/input -v \$(pwd)/output:/app/output pdf-extractor"
echo "3. Check the 'output' directory for JSON results"
echo ""
echo "Example:"
echo "docker run -v \$(pwd)/input:/app/input -v \$(pwd)/output:/app/output pdf-extractor"
