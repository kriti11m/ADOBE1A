<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# PDF Structure Extractor - Copilot Instructions

This is a Python project for extracting structured outlines from PDF documents using PyMuPDF (fitz).

## Project Context
- **Purpose**: Extract title and headings (H1, H2, H3) from PDF files with page numbers
- **Library**: PyMuPDF (fitz) for PDF processing
- **Output**: JSON format with structured document outline
- **Constraints**: Offline processing, ≤200MB memory, ≤10s runtime, ≤50 pages
- **Deployment**: Docker containerized for portability

## Key Components
- `pdf_extractor.py`: Main extraction logic with font-based heuristics
- `Dockerfile`: Container configuration for offline processing
- `requirements.txt`: Minimal dependencies (only PyMuPDF)
- Build scripts for Windows (`.bat`) and Unix (`.sh`)

## Coding Guidelines
- Follow Python best practices and type hints
- Use font size and style heuristics for heading detection
- Implement error handling for malformed PDFs
- Keep memory usage minimal and processing fast
- Ensure all functionality works offline without external APIs
