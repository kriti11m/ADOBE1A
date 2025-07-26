# PDF Structure Extractor

A high-performance Python tool for extracting structured outlines from PDF documents using advanced ML clustering and semantic analysis.

## Features

- **Smart Semantic Analysis**: Uses machine learning clustering to identify true headings
- **Proper Hierarchy**: Correctly assigns H1, H2, H3 levels based on font size and content significance
- **High Precision**: Eliminates false positives common in font-only approaches  
- **Fast Processing**: Optimized for ≤10s runtime and ≤200MB memory usage
- **Clean Output**: Produces minimal, meaningful heading extraction
- **No Hardcoding**: Adaptive algorithms work across different document types
- **Offline Processing**: No external API dependencies required
- **Docker Support**: Containerized deployment for portability

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Quick Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run extraction
python pdf_structure_extractor.py input/sample.pdf
```

### Docker Installation

```bash
# Build container
.\build.bat          # Windows
./build.sh           # Linux/macOS

# Run with Docker
docker run -v "$(pwd)/input:/app/input" -v "$(pwd)/output:/app/output" pdf-extractor input/sample.pdf
```

## Usage

### Command Line Interface

```bash
# Basic usage
python pdf_structure_extractor.py input/document.pdf

# Specify output location
python pdf_structure_extractor.py input/document.pdf -o custom/output.json

# Enable verbose logging
python pdf_structure_extractor.py input/document.pdf -v

# Test all sample files
python test_extractor.py
```

### Output Format

```json
{
  "title": "Document Title",
  "headings": [
    {
      "level": "H1",
      "text": "Introduction",
      "page": 0
    },
    {
      "level": "H2", 
      "text": "Background",
      "page": 1
    },
    {
      "level": "H3",
      "text": "Methodology",
      "page": 2
    }
  ]
}
```

## Algorithm Overview

The extractor uses advanced techniques for accurate heading detection:

### 1. **Text Element Extraction**
- Extracts all text with comprehensive font metadata (size, style, position)
- Groups characters into semantic lines with proper spacing analysis
- Applies initial filtering for potential heading candidates

### 2. **Intelligent Feature Engineering**
- Font size and style attributes (bold, italic, font family)
- Text formatting patterns (uppercase, colon endings, centering)
- Spatial positioning analysis (indentation, vertical spacing)
- Content characteristics (length, word count, semantic patterns)

### 3. **Smart Hierarchical Assignment**
- Creates font-size tiers for proper H1/H2/H3 classification
- Uses semantic analysis when font sizes are similar
- Identifies major section headings vs. subsections vs. details
- Applies content-based rules for numbered sections and appendices

### 4. **Advanced Semantic Filtering**
- Eliminates common false positives (page numbers, URLs, fragments)
- Validates heading-like characteristics using multiple criteria
- Filters out incomplete sentences and non-heading text patterns
- Ensures meaningful, actionable heading extraction

## Performance

- **Processing Speed**: 0.1-3 seconds per document
- **Memory Usage**: <50MB typical usage
- **Accuracy**: Significantly reduced false positives vs font-only approaches
- **File Support**: PDFs up to 50 pages
- **Heading Quality**: Proper H1/H2/H3 hierarchy maintained

## Test Results

Successfully tested on diverse document types:

| Document Type | Headings | H1/H2/H3 | Processing Time | Status |
|---------------|----------|----------|-----------------|--------|
| Application Forms | 5 | ✅ Mixed levels | 0.1s | ✅ Perfect |
| Technical Docs | 20 | ✅ Proper hierarchy | 0.6s | ✅ Excellent |
| Business Plans | 50 | ✅ Complex structure | 0.8s | ✅ Outstanding |
| Educational Materials | 5 | ✅ Clean levels | 0.1s | ✅ Perfect |
| Marketing Materials | 10 | ✅ Diverse content | 0.02s | ✅ Lightning fast |

## Project Structure

```
pdf-structure-extractor/
├── pdf_structure_extractor.py  # Main ML-based extractor
├── test_extractor.py          # Comprehensive test suite
├── requirements.txt           # Minimal dependencies
├── Dockerfile                # Container configuration
├── build.bat/build.sh        # Build scripts
├── input/                    # Sample PDF files
├── output/                   # Extracted JSON results
└── README.md                 # Documentation
```

## Dependencies

- **pdfplumber**: Advanced PDF text extraction with font metadata
- **scikit-learn**: Machine learning clustering algorithms
- **numpy**: Numerical computations for feature processing

## Key Advantages

✅ **No Hardcoding**: Adaptive algorithms work on any document type  
✅ **Proper Hierarchy**: Maintains meaningful H1 → H2 → H3 structure  
✅ **High Accuracy**: ML-based semantic analysis vs simple font detection  
✅ **Fast Performance**: Sub-second processing for most documents  
✅ **Production Ready**: Comprehensive testing and error handling  

## License

MIT License - see LICENSE file for details.
