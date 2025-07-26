#!/usr/bin/env python3
"""
Quick test script for the PDF Structure Extractor
"""

import subprocess
import sys
from pathlib import Path
import json

def test_extractor():
    """Test the PDF structure extractor on sample files."""
    print("🧪 Testing PDF Structure Extractor...")
    
    input_dir = Path("input")
    output_dir = Path("output")
    
    # Find sample PDF files
    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ No PDF files found in input/ directory")
        print("📁 Please add some PDF files to test")
        return False
    
    success_count = 0
    total_files = len(pdf_files)
    
    for pdf_file in pdf_files:
        print(f"\n📄 Testing: {pdf_file.name}")
        
        try:
            # Run the extractor
            result = subprocess.run([
                sys.executable, "pdf_structure_extractor.py", str(pdf_file)
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Check if output file was created
                output_file = output_dir / f"{pdf_file.stem}_structure.json"
                
                if output_file.exists():
                    # Load and validate JSON
                    with open(output_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    heading_count = len(data.get('headings', []))
                    title = data.get('title', 'No title')
                    
                    print(f"✅ Success: {heading_count} headings extracted")
                    print(f"📝 Title: {title[:50]}...")
                    success_count += 1
                else:
                    print("❌ Output file not created")
            else:
                print(f"❌ Extraction failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print("❌ Extraction timed out (>30s)")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n📊 Test Results: {success_count}/{total_files} files processed successfully")
    
    if success_count == total_files:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️  Some tests failed")
        return False

if __name__ == "__main__":
    test_extractor()
