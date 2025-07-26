@echo off
echo Building PDF Structure Extractor Docker image...
docker build -t pdf-extractor .

if not exist "input" mkdir input
if not exist "output" mkdir output

echo Docker image built successfully!
echo.
echo Usage:
echo 1. Place your PDF files in the 'input' directory
echo 2. Run: docker run -v %cd%/input:/app/input -v %cd%/output:/app/output pdf-extractor
echo 3. Check the 'output' directory for JSON results
echo.
echo Example:
echo docker run -v %cd%/input:/app/input -v %cd%/output:/app/output pdf-extractor
