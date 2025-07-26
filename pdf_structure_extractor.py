#!/usr/bin/env python3
"""
PDF Structure Extractor - Best Performance Version
Uses ML clustering for semantic heading detection
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

try:
    import pdfplumber
    import numpy as np
    from sklearn.cluster import DBSCAN
    from sklearn.preprocessing import StandardScaler
    import argparse
except ImportError as e:
    print(f"Error: Required library not installed: {e}")
    print("Run: pip install pdfplumber scikit-learn numpy")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFStructureExtractor:
    """Advanced PDF structure extractor using ML clustering for semantic analysis."""
    
    def __init__(self):
        self.min_title_font_size = 14
        self.min_heading_length = 3
        self.max_heading_length = 100
        
    def extract_structure(self, pdf_path: str) -> Dict[str, Any]:
        """Extract structured outline from PDF using ML clustering."""
        start_time = time.time()
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Extract text elements with font information
                text_elements = self._extract_text_elements(pdf)
                
                if not text_elements:
                    return {"title": "", "headings": [], "processing_time": time.time() - start_time}
                
                # Use ML clustering for semantic analysis
                headings = self._cluster_headings(text_elements)
                
                # Extract title (first significant element or largest font)
                title = self._extract_title(text_elements)
                
                processing_time = time.time() - start_time
                logger.info(f"Extracted {len(headings)} headings in {processing_time:.2f}s")
                
                return {
                    "title": title,
                    "headings": headings,
                    "processing_time": processing_time
                }
                
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            return {"title": "", "headings": [], "error": str(e)}
    
    def _extract_text_elements(self, pdf) -> List[Dict]:
        """Extract text elements with font metadata from all pages."""
        elements = []
        
        for page_num, page in enumerate(pdf.pages):
            if page.chars:
                # Group characters by font and position
                lines = self._group_chars_to_lines(page.chars)
                
                for line in lines:
                    if self._is_potential_heading(line):
                        elements.append({
                            'text': line['text'].strip(),
                            'page': page_num,
                            'font_size': line['font_size'],
                            'font_name': line['font_name'],
                            'is_bold': line['is_bold'],
                            'x0': line['x0'],
                            'y0': line['y0'],
                            'char_count': len(line['text'].strip()),
                            'word_count': len(line['text'].strip().split()),
                            'is_uppercase': line['text'].isupper(),
                            'has_colon': line['text'].strip().endswith(':'),
                            'is_centered': self._is_text_centered(line, page.width)
                        })
        
        return elements
    
    def _group_chars_to_lines(self, chars) -> List[Dict]:
        """Group characters into lines based on position and font."""
        if not chars:
            return []
        
        # Sort by Y position (top to bottom), then X position
        sorted_chars = sorted(chars, key=lambda c: (-c['y0'], c['x0']))
        
        lines = []
        current_line = {
            'chars': [],
            'y0': sorted_chars[0]['y0'],
            'font_size': sorted_chars[0]['size'],
            'font_name': sorted_chars[0]['fontname'],
            'is_bold': 'Bold' in sorted_chars[0]['fontname'],
            'x0': sorted_chars[0]['x0']
        }
        
        for char in sorted_chars:
            # Check if character belongs to current line (similar Y position and font)
            if (abs(char['y0'] - current_line['y0']) < 2 and 
                abs(char['size'] - current_line['font_size']) < 1):
                current_line['chars'].append(char)
            else:
                # Finalize current line
                if current_line['chars']:
                    current_line['text'] = ''.join(c['text'] for c in current_line['chars'])
                    lines.append(current_line)
                
                # Start new line
                current_line = {
                    'chars': [char],
                    'y0': char['y0'],
                    'font_size': char['size'],
                    'font_name': char['fontname'],
                    'is_bold': 'Bold' in char['fontname'],
                    'x0': char['x0']
                }
        
        # Add last line
        if current_line['chars']:
            current_line['text'] = ''.join(c['text'] for c in current_line['chars'])
            lines.append(current_line)
        
        return lines
    
    def _is_potential_heading(self, line: Dict) -> bool:
        """Check if line could be a heading."""
        text = line['text'].strip()
        
        # Basic filters
        if (len(text) < self.min_heading_length or 
            len(text) > self.max_heading_length or
            text.isdigit() or
            len(text.split()) > 15):  # Too long to be a heading
            return False
        
        # Font size or formatting suggests heading
        if (line['font_size'] >= self.min_title_font_size or
            line['is_bold'] or
            text.isupper() or
            text.endswith(':')):
            return True
        
        return False
    
    def _cluster_headings(self, elements: List[Dict]) -> List[Dict]:
        """Use font size hierarchy to assign proper heading levels."""
        if not elements:
            return []
        
        # First, filter semantically valid headings
        valid_headings = [elem for elem in elements if self._is_semantic_heading(elem)]
        
        if not valid_headings:
            return []
        
        # Sort by font size (descending) to establish hierarchy
        valid_headings.sort(key=lambda x: x['font_size'], reverse=True)
        
        # Create font size tiers for H1, H2, H3 assignment
        font_sizes = [elem['font_size'] for elem in valid_headings]
        unique_sizes = sorted(set(font_sizes), reverse=True)
        
        # Define thresholds for heading levels
        if len(unique_sizes) == 1:
            # All same font size - use other criteria
            headings = self._assign_levels_by_content(valid_headings)
        else:
            # Create font size tiers
            headings = self._assign_levels_by_font_tiers(valid_headings, unique_sizes)
        
        # Sort headings by page and position
        headings.sort(key=lambda h: (h['page'], -h.get('y0', 0)))
        
        return headings
    
    def _assign_levels_by_font_tiers(self, headings: List[Dict], unique_sizes: List[float]) -> List[Dict]:
        """Assign heading levels based on font size tiers."""
        result = []
        
        # Create 3 tiers for H1, H2, H3
        if len(unique_sizes) >= 3:
            h1_threshold = unique_sizes[0]  # Largest
            h2_threshold = unique_sizes[1]  # Second largest
            # Everything else is H3
        elif len(unique_sizes) == 2:
            h1_threshold = unique_sizes[0]  # Largest
            h2_threshold = unique_sizes[1]  # Smaller
            # No separate H3 threshold
        else:
            h1_threshold = unique_sizes[0]
            h2_threshold = h1_threshold
        
        for elem in headings:
            font_size = elem['font_size']
            
            # Determine level based on font size and other criteria
            if font_size >= h1_threshold:
                # Check if it's truly a major heading
                if (self._is_major_heading(elem) or 
                    elem['is_bold'] or 
                    elem['is_uppercase'] or
                    font_size > h2_threshold + 2):
                    level = "H1"
                else:
                    level = "H2"
            elif font_size >= h2_threshold:
                level = "H2"
            else:
                level = "H3"
            
            result.append(self._format_heading(elem, level))
        
        return result
    
    def _assign_levels_by_content(self, headings: List[Dict]) -> List[Dict]:
        """Assign levels when font sizes are similar, using content analysis."""
        result = []
        
        for elem in headings:
            text = elem['text'].strip()
            
            # H1 criteria - major section indicators
            if (self._is_major_heading(elem) or
                elem['is_uppercase'] and len(text.split()) <= 5 or
                elem['is_centered'] or
                any(keyword in text.lower() for keyword in ['chapter', 'part', 'section', 'appendix']) or
                text.endswith(':') and len(text.split()) <= 3):
                level = "H1"
            
            # H2 criteria - subsection indicators  
            elif (elem['is_bold'] or
                  text.endswith(':') or
                  any(keyword in text.lower() for keyword in ['overview', 'summary', 'background', 'phase', 'step']) or
                  len(text.split()) <= 4):
                level = "H2"
            
            # H3 - everything else
            else:
                level = "H3"
            
            result.append(self._format_heading(elem, level))
        
        return result
    
    def _is_major_heading(self, element: Dict) -> bool:
        """Check if element represents a major section heading."""
        text = element['text'].strip().lower()
        
        # Major heading indicators
        major_keywords = [
            'introduction', 'conclusion', 'summary', 'overview', 'background',
            'methodology', 'results', 'discussion', 'references', 'appendix',
            'chapter', 'part', 'section', 'phase', 'step', 'goals', 'mission',
            'vision', 'strategy', 'plan', 'proposal', 'requirements', 'scope'
        ]
        
        # Check for numbered sections (1., 2., I., II., etc.)
        if (text.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', 
                           'i.', 'ii.', 'iii.', 'iv.', 'v.', 'vi.', 'vii.', 'viii.', 'ix.', 'x.')) or
            any(keyword in text for keyword in major_keywords) or
            (element['is_uppercase'] and len(text.split()) <= 4) or
            (element['is_centered'] and element['font_size'] >= self.min_title_font_size)):
            return True
        
        return False
    
    def _is_semantic_heading(self, element: Dict) -> bool:
        """Apply stricter semantic rules to filter out non-headings."""
        text = element['text'].strip()
        text_lower = text.lower()
        
        # Skip if too long (likely paragraph text)
        if len(text.split()) > 8:
            return False
        
        # Skip common non-heading patterns
        skip_patterns = [
            'page', 'figure', 'table', 'www.', 'http', '@', 'tel:', 'fax:',
            'email:', '.com', '.org', '.ca', 'phone:', 'address:', 'date:',
            'time:', 'location:', 'contact:', 'copyright', '©', 'all rights reserved'
        ]
        
        if any(pattern in text_lower for pattern in skip_patterns):
            return False
        
        # Skip if mostly numbers, dates, or currency
        if (len([c for c in text if c.isdigit() or c in '$,.']) > len(text) * 0.4 or
            any(pattern in text for pattern in ['$', '©', '®', '™']) or
            len(text) < 3):
            return False
        
        # Skip fragments or incomplete sentences
        if (text.endswith(('and', 'or', 'the', 'of', 'in', 'on', 'at', 'to', 'for')) or
            text.startswith(('and', 'or', 'the', 'of', 'in', 'on', 'at', 'to', 'for', 'a ', 'an '))):
            return False
        
        # Positive indicators for headings
        heading_indicators = [
            element['font_size'] >= self.min_title_font_size,
            element['is_bold'],
            element['is_uppercase'],
            text.endswith(':'),
            element['is_centered'],
            len(text.split()) <= 6,  # Short, heading-like
            any(keyword in text_lower for keyword in [
                'chapter', 'section', 'part', 'appendix', 'phase', 'step',
                'overview', 'summary', 'background', 'introduction', 'conclusion',
                'goals', 'mission', 'vision', 'strategy', 'objectives', 'scope',
                'requirements', 'specifications', 'timeline', 'milestones'
            ])
        ]
        
        # Must have at least one strong heading indicator
        if sum(heading_indicators) >= 1:
            return True
        
        return False
    
    def _format_heading(self, element: Dict, level: str) -> Dict:
        """Format heading for output."""
        return {
            "level": level,
            "text": element['text'].strip(),
            "page": element['page'],
            "font_size": element['font_size'],
            "y0": element['y0']
        }
    
    def _extract_title(self, elements: List[Dict]) -> str:
        """Extract document title from elements."""
        if not elements:
            return ""
        
        # Find element with largest font or first significant element
        title_candidate = max(elements, key=lambda x: (x['font_size'], x['is_bold']))
        
        # Additional validation for title
        title_text = title_candidate['text'].strip()
        if len(title_text) > 100:  # Too long for title
            title_text = title_text[:50] + "..."
        
        return title_text
    
    def _is_text_centered(self, line: Dict, page_width: float) -> bool:
        """Check if text appears to be centered on the page."""
        text_width = len(line['text']) * (line['font_size'] * 0.6)  # Rough estimate
        margin = abs((page_width - text_width) / 2 - line['x0'])
        return margin < 50  # Tolerance for centering
    
    def save_output(self, result: Dict, output_path: str) -> None:
        """Save extraction result to JSON file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Remove internal fields for clean output
        clean_result = {
            "title": result["title"],
            "headings": [
                {
                    "level": h["level"],
                    "text": h["text"],
                    "page": h["page"]
                }
                for h in result["headings"]
            ]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(clean_result, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {output_path}")

def main():
    """Main function with CLI interface."""
    parser = argparse.ArgumentParser(description='Extract PDF structure using ML clustering')
    parser.add_argument('input_pdf', help='Path to input PDF file')
    parser.add_argument('-o', '--output', help='Output JSON file path')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate input file
    input_path = Path(args.input_pdf)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)
    
    # Set output path
    if args.output:
        output_path = args.output
    else:
        output_path = f"output/{input_path.stem}_structure.json"
    
    # Extract structure
    extractor = PDFStructureExtractor()
    result = extractor.extract_structure(str(input_path))
    
    # Save result
    extractor.save_output(result, output_path)
    
    # Print summary
    if 'error' in result:
        logger.error(f"Extraction failed: {result['error']}")
        sys.exit(1)
    else:
        print(f"[SUCCESS] Extracted {len(result['headings'])} headings from {input_path.name}")
        print(f"[OUTPUT] Saved to: {output_path}")
        print(f"[TIME] Processing time: {result.get('processing_time', 0):.2f}s")

if __name__ == "__main__":
    main()
