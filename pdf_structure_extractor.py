#!/usr/bin/env python3
"""
PDF Structure Extractor using PyMuPDF (fitz)
Extracts title and headings (H1, H2, H3) from PDF files with page numbers
Optimized for offline processing with multilingual support and minimal memory usage
"""

import json
import sys
import time
import unicodedata
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from collections import Counter, defaultdict

try:
    import fitz  # PyMuPDF
except ImportError as e:
    print(f"Error: PyMuPDF not installed: {e}")
    print("Run: pip install PyMuPDF")
    sys.exit(1)


# Set up basic logging
logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class MultilingualPDFExtractor:
    """
    PDF structure extractor that works with multiple languages and writing systems.
    Uses font analysis and content patterns to identify document structure.
    """
    
    def __init__(self):
        """Set up the extractor with default settings."""
        self.page_limit = 50  
        self.memory_threshold = 1000  
        
        # Load language patterns
        self._setup_language_patterns()
        
    def _setup_language_patterns(self) -> None:
        """Load structural keywords and patterns for different languages."""
        
        # Common structural terms by language
        self.lang_keywords = {
            # Western European languages
            'latin': {
                'english': ['introduction', 'overview', 'summary', 'background', 'conclusion',
                          'methodology', 'results', 'discussion', 'references', 'appendix',
                          'acknowledgments', 'abstract', 'preface', 'contents', 'index',
                          'objectives', 'requirements', 'specifications', 'timeline',
                          'approach', 'evaluation', 'criteria', 'milestones', 'scope'],
                          
                'spanish': ['introducción', 'resumen', 'antecedentes', 'conclusión',
                           'metodología', 'resultados', 'discusión', 'referencias', 'apéndice',
                           'agradecimientos', 'resumen', 'prefacio', 'contenidos', 'índice',
                           'objetivos', 'requisitos', 'especificaciones', 'cronograma',
                           'enfoque', 'evaluación', 'criterios', 'hitos', 'alcance'],
                           
                'french': ['introduction', 'aperçu', 'résumé', 'contexte', 'conclusion',
                          'méthodologie', 'résultats', 'discussion', 'références', 'annexe',
                          'remerciements', 'résumé', 'préface', 'contenu', 'index',
                          'objectifs', 'exigences', 'spécifications', 'calendrier',
                          'approche', 'évaluation', 'critères', 'jalons', 'portée'],
                          
                'german': ['einführung', 'überblick', 'zusammenfassung', 'hintergrund', 'schluss',
                          'methodik', 'ergebnisse', 'diskussion', 'referenzen', 'anhang',
                          'danksagungen', 'zusammenfassung', 'vorwort', 'inhalt', 'index',
                          'ziele', 'anforderungen', 'spezifikationen', 'zeitplan',
                          'ansatz', 'bewertung', 'kriterien', 'meilensteine', 'umfang']
            },
            
            # Slavic languages
            'cyrillic': {
                'russian': ['введение', 'обзор', 'резюме', 'предпосылки', 'заключение',
                           'методология', 'результаты', 'обсуждение', 'ссылки', 'приложение',
                           'благодарности', 'аннотация', 'предисловие', 'содержание', 'индекс',
                           'цели', 'требования', 'спецификации', 'график',
                           'подход', 'оценка', 'критерии', 'вехи', 'область']
            },
            
            # Middle Eastern languages
            'arabic': {
                'arabic': ['مقدمة', 'نظرة عامة', 'ملخص', 'خلفية', 'خاتمة',
                          'منهجية', 'نتائج', 'مناقشة', 'مراجع', 'ملحق',
                          'شكر وتقدير', 'مستخلص', 'تمهيد', 'محتويات', 'فهرس',
                          'أهداف', 'متطلبات', 'مواصفات', 'جدول زمني',
                          'نهج', 'تقييم', 'معايير', 'معالم', 'نطاق']
            },
            
            # Asian languages
            'cjk': {
                'chinese': ['引言', '概述', '摘要', '背景', '结论',
                           '方法论', '结果', '讨论', '参考文献', '附录',
                           '致谢', '摘要', '前言', '目录', '索引',
                           '目标', '要求', '规格', '时间表',
                           '方法', '评估', '标准', '里程碑', '范围'],
                           
                'japanese': ['はじめに', '概要', '要約', '背景', '結論',
                            '方法論', '結果', '議論', '参考文献', '付録',
                            '謝辞', '要旨', '序文', '目次', '索引',
                            '目標', '要件', '仕様', 'スケジュール',
                            'アプローチ', '評価', '基準', 'マイルストーン', '範囲']
            }
        }
        
        # Number formats for different writing systems
        self.number_patterns = {
            'latin': [
                r'^\d+\.?\s+\w+',  
                r'^\d+\.\d+\.?\s+\w+',  
                r'^[IVX]+\.?\s+\w+',  
                r'^[a-zA-Z]\)?\s+\w+',  
                r'^(chapter|section|part|appendix)\s+\d+',  
            ],
            'cyrillic': [
                r'^\d+\.?\s+\w+',  
                r'^\d+\.\d+\.?\s+\w+',  
                r'^(глава|раздел|часть|приложение)\s+\d+',  
            ],
            'arabic': [
                r'^[\u0660-\u0669]+\.?\s+\w+',  
                r'^\d+\.?\s+\w+',  
                r'^(فصل|قسم|جزء|ملحق)\s+[\d\u0660-\u0669]+',  
            ],
            'cjk': [
                r'^[一二三四五六七八九十]+[、.]?\s*\w+',  
                r'^\d+[、.]?\s*\w+',  
                r'^第[一二三四五六七八九十\d]+[章节部分]\s*\w+',  
                r'^[①②③④⑤⑥⑦⑧⑨⑩]\s*\w+',  
            ]
        }
    
    def extract_structure(self, pdf_path: str) -> Dict[str, Any]:
        """
        Main method to extract title and headings from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dict containing title and outline structure
        """
        start_time = time.time()
        
        try:
            doc = fitz.open(pdf_path)
            total_pages = min(len(doc), self.page_limit)
            
            # Get all text blocks from the document
            all_blocks = self._get_text_blocks(doc, total_pages)
            
            if not all_blocks:
                doc.close()
                return {"title": "", "outline": []}
            
            # Figure out what language this document is in
            doc_lang = self._guess_language(all_blocks)
            
            # Analyze the document structure
            structure_info = self._analyze_structure(all_blocks, doc_lang)
            
            # Find the document title
            title = self._find_title(all_blocks, structure_info, doc_lang)
            
            # Extract the heading structure
            outline = self._build_outline(all_blocks, structure_info, title, doc_lang)
            
            doc.close()
            
            # Check if we're taking too long
            elapsed = time.time() - start_time
            if elapsed > 8:
                logger.warning(f"Processing time getting long: {elapsed:.2f}s")
            
            return {
                "title": title,
                "outline": outline
            }
                
        except Exception as e:
            logger.error(f"Failed to process PDF {pdf_path}: {e}")
            return {"title": "", "outline": []}
    
    def _get_text_blocks(self, doc: fitz.Document, page_count: int) -> List[Dict[str, Any]]:
        """Extract text blocks from PDF pages."""
        blocks = []
        
        for page_idx in range(page_count):
            try:
                page = doc[page_idx]
                text_data = page.get_text("dict")
                page_rect = page.rect
                
                for block in text_data.get("blocks", []):
                    if "lines" not in block:  
                        continue
                    
                    # Combine lines into blocks
                    processed_blocks = self._process_block_lines(
                        block["lines"], page_idx, page_rect
                    )
                    blocks.extend(processed_blocks)
                    
                    # Don't use too much memory
                    if len(blocks) > self.memory_threshold:
                        logger.warning("Hit memory limit, stopping block extraction")
                        return blocks[:self.memory_threshold]
                
            except Exception as e:
                logger.error(f"Error on page {page_idx}: {e}")
                continue
        
        return blocks
    
    def _process_block_lines(self, lines: List[Dict], page_num: int, 
                            page_rect: fitz.Rect) -> List[Dict[str, Any]]:
        """Convert line data into consolidated text blocks."""
        result_blocks = []
        
        for line in lines:
            spans = line.get("spans", [])
            if not spans:
                continue
            
            # Group spans that are close together
            span_groups = self._group_nearby_spans(spans)
            
            for group in span_groups:
                # Make a single block from the span group
                block_info = self._make_text_block(group, page_num, page_rect)
                
                if block_info and self._is_useful_text(block_info['text']):
                    result_blocks.append(block_info)
        
        return result_blocks
    
    def _group_nearby_spans(self, spans: List[Dict]) -> List[List[Dict]]:
        """Group spans that are positioned close to each other."""
        if not spans:
            return []
        
        # Sort by position
        sorted_spans = sorted(spans, key=lambda s: (s["bbox"][1], s["bbox"][0]))
        
        groups = []
        current_group = [sorted_spans[0]]
        
        for i in range(1, len(sorted_spans)):
            curr = sorted_spans[i]
            prev = sorted_spans[i-1]
            
            # Check distance between spans
            y_gap = abs(curr["bbox"][1] - prev["bbox"][1])
            x_gap = abs(curr["bbox"][0] - prev["bbox"][2])
            
            if y_gap < 5 and x_gap < 20:  
                current_group.append(curr)
            else:
                groups.append(current_group)
                current_group = [curr]
        
        groups.append(current_group)
        return groups
    
    def _make_text_block(self, spans: List[Dict], page_num: int, 
                        page_rect: fitz.Rect) -> Optional[Dict[str, Any]]:
        """Create a text block from a group of spans."""
        if not spans:
            return None
        
        # Combine text from spans
        text_parts = []
        sizes = []
        combined_flags = 0
        
        for span in spans:
            text = span["text"].strip()
            if text:
                # Clean up Unicode
                clean_text = unicodedata.normalize('NFC', text)
                text_parts.append(clean_text)
                sizes.append(span["size"])
                combined_flags |= span["flags"]
        
        if not text_parts:
            return None
        
        # Join text with spaces
        full_text = " ".join(text_parts)
        
        # Use the largest font size
        main_size = max(sizes) if sizes else 12
        
        # Calculate bounding box
        x1 = min(span["bbox"][0] for span in spans)
        y1 = min(span["bbox"][1] for span in spans)
        x2 = max(span["bbox"][2] for span in spans)
        y2 = max(span["bbox"][3] for span in spans)
        
        # Figure out what script this text uses
        script = self._get_script_type(full_text)
        
        return {
            'text': full_text,
            'page': page_num,
            'font_size': main_size,
            'font_name': spans[0]["font"],
            'flags': combined_flags,
            'bbox': [x1, y1, x2, y2],
            'x0': x1,
            'y0': y1,
            'x1': x2,
            'y1': y2,
            'page_width': page_rect.width,
            'page_height': page_rect.height,
            'char_count': len(full_text),
            'word_count': len(full_text.split()),
            'line_height': y2 - y1,
            'script_type': script
        }
    
    def _get_script_type(self, text: str) -> str:
        """Figure out what writing system the text uses."""
        if not text:
            return 'unknown'
        
        script_counts = defaultdict(int)
        
        for char in text:
            if char.isspace() or char.isdigit() or char in '.,;:!?-()[]{}':
                continue
            
            # Check Unicode category
            try:
                char_name = unicodedata.name(char).split()[0]
                
                if any(s in char_name for s in ['LATIN', 'LETTER']):
                    script_counts['latin'] += 1
                elif 'CYRILLIC' in char_name:
                    script_counts['cyrillic'] += 1
                elif any(s in char_name for s in ['ARABIC', 'PERSIAN']):
                    script_counts['arabic'] += 1
                elif any(s in char_name for s in ['CJK', 'HIRAGANA', 'KATAKANA', 'HANGUL']):
                    script_counts['cjk'] += 1
                else:
                    script_counts['other'] += 1
                    
            except ValueError:
                script_counts['other'] += 1
        
        if not script_counts:
            return 'latin'  
        
        return max(script_counts.items(), key=lambda x: x[1])[0]
    
    def _guess_language(self, blocks: List[Dict[str, Any]]) -> str:
        """Try to determine what language the document is written in."""
        # Get some sample text from early blocks
        sample = ""
        char_limit = 1000  
        
        for block in blocks[:20]:  
            if len(sample) >= char_limit:
                break
            sample += " " + block['text']
        
        if not sample:
            return 'english'  
        
        # Check what script it uses
        script = self._get_script_type(sample)
        
        if script == 'latin':
            return self._detect_latin_lang(sample.lower())
        elif script == 'cyrillic':
            return self._detect_cyrillic_lang(sample)
        elif script == 'arabic':
            return self._detect_arabic_lang(sample)
        elif script == 'cjk':
            return self._detect_cjk_lang(sample)
        
        return 'english'  
    
    def _detect_latin_lang(self, text: str) -> str:
        """Detect specific language for Latin script text."""
        # Simple keyword matching
        lang_scores = {}
        
        for lang, keywords in self.lang_keywords['latin'].items():
            score = sum(1 for word in keywords if word in text)
            lang_scores[lang] = score
        
        if lang_scores:
            best_lang = max(lang_scores.items(), key=lambda x: x[1])[0]
            if lang_scores[best_lang] > 0:
                return best_lang
        
        return 'english'  
    
    def _detect_cyrillic_lang(self, text: str) -> str:
        """Detect Cyrillic language."""
        # Look for Ukrainian-specific characters
        if any(c in text for c in 'іїє'):
            return 'ukrainian'
        return 'russian'  
    
    def _detect_arabic_lang(self, text: str) -> str:
        """Detect Arabic script language."""
        # Persian has some unique characters
        if any(c in text for c in 'پچژگ'):
            return 'persian'
        return 'arabic'  
    
    def _detect_cjk_lang(self, text: str) -> str:
        """Detect CJK language."""
        # Basic character detection
        if any(c in text for c in 'ひらがなカタカナ'):
            return 'japanese'
        elif any(c in text for c in '한글'):
            return 'korean'
        return 'chinese'  
    
    def _is_useful_text(self, text: str) -> bool:
        """Check if text block contains useful content."""
        if not text or len(text.strip()) < 2:
            return False
        
        # Skip very long paragraphs
        if len(text) > 300:
            return False
        
        # Need some actual letters/characters
        useful_chars = sum(1 for c in text if c.isalnum() or ord(c) > 127)
        if useful_chars < 2:
            return False
        
        return True
    
    def _analyze_structure(self, blocks: List[Dict[str, Any]], 
                          language: str) -> Dict[str, Any]:
        """Analyze the document structure to understand formatting patterns."""
        if not blocks:
            return {}
        
        # Look at font usage
        font_sizes = [b['font_size'] for b in blocks]
        font_names = [b['font_name'] for b in blocks]
        
        size_counts = Counter(font_sizes)
        name_counts = Counter(font_names)
        
        # Basic statistics
        sorted_sizes = sorted(font_sizes)
        n = len(sorted_sizes)
        
        font_info = {
            'average': sum(font_sizes) / n,
            'median': sorted_sizes[n // 2],
            'largest': max(font_sizes),
            'smallest': min(font_sizes),
            'p75': sorted_sizes[int(n * 0.75)] if n > 4 else sorted_sizes[-1],
            'p90': sorted_sizes[int(n * 0.90)] if n > 10 else sorted_sizes[-1],
            'p95': sorted_sizes[int(n * 0.95)] if n > 20 else sorted_sizes[-1],
            'all_sizes': sorted(set(font_sizes), reverse=True),
            'size_counts': size_counts,
            'common_font': name_counts.most_common(1)[0][0] if name_counts else ''
        }
        
        # Look for structural patterns
        content_info = self._find_content_patterns(blocks, language)
        
        # Analyze layout
        layout_info = self._analyze_layout(blocks)
        
        return {
            'fonts': font_info,
            'content': content_info,
            'layout': layout_info,
            'language': language,
            'block_count': len(blocks)
        }
    
    def _find_content_patterns(self, blocks: List[Dict[str, Any]], 
                              language: str) -> Dict[str, Any]:
        """Look for patterns in the content that indicate structure."""
        patterns = {
            'numbered_items': [],
            'keywords': [],
            'caps_text': [],
            'colon_endings': [],
            'short_lines': []
        }
        
        for block in blocks:
            text = block['text'].strip()
            text_lower = text.lower()
            script = block.get('script_type', 'latin')
            
            # Check for numbering
            if self._has_numbering(text, script):
                patterns['numbered_items'].append(block)
            
            # Look for structural keywords
            if self._has_keywords(text_lower, language):
                patterns['keywords'].append(block)
            
            # Check capitalization
            if self._is_caps_text(text, script):
                patterns['caps_text'].append(block)
            
            # Lines ending with colons
            if self._ends_with_colon(text, script):
                patterns['colon_endings'].append(block)
            
            # Short descriptive lines
            if self._is_short_line(text, script):
                patterns['short_lines'].append(block)
        
        return patterns
    
    def _has_numbering(self, text: str, script: str) -> bool:
        """Check if text starts with a number or bullet pattern."""
        patterns = self.number_patterns.get(script, self.number_patterns['latin'])
        
        return any(re.match(pattern, text, re.IGNORECASE | re.UNICODE) for pattern in patterns)
    
    def _has_keywords(self, text_lower: str, language: str) -> bool:
        """Check if text contains structural keywords."""
        # Find keywords for this language
        for script_family, languages in self.lang_keywords.items():
            if language in languages:
                keywords = languages[language]
                return any(keyword in text_lower for keyword in keywords)
        
        # Fall back to English
        english_words = self.lang_keywords['latin']['english']
        return any(word in text_lower for word in english_words)
    
    def _is_caps_text(self, text: str, script: str) -> bool:
        """Check if text is meaningfully capitalized."""
        if script in ['arabic', 'cjk']:
            # These don't have caps
            return False
        
        if not text.isupper():
            return False
        
        # Reasonable length
        if not (5 <= len(text) <= 100):
            return False
        
        # Not too many words
        if len(text.split()) > 15:
            return False
        
        return True
    
    def _ends_with_colon(self, text: str, script: str) -> bool:
        """Check if text ends with colon or similar punctuation."""
        endings = {
            'latin': [':'],
            'cyrillic': [':'],
            'arabic': [':', '؛'],  
            'cjk': [':', '：', '。']  
        }
        
        punct_list = endings.get(script, [':'])
        return any(text.endswith(p) for p in punct_list) and len(text.split()) <= 12
    
    def _is_short_line(self, text: str, script: str) -> bool:
        """Check if this is a short descriptive line."""
        # For Asian languages, count characters instead of words
        if script == 'cjk':
            return 5 <= len(text) <= 50
        else:
            return 3 <= len(text.split()) <= 15 and len(text) <= 150
    
    def _analyze_layout(self, blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Look at how text is positioned on the page."""
        layout = {
            'centered': [],
            'left_side': [],
            'right_side': [],
            'isolated': [],
            'top_of_page': []
        }
        
        # Group by page
        by_page = defaultdict(list)
        for block in blocks:
            by_page[block['page']].append(block)
        
        for page_num, page_blocks in by_page.items():
            if not page_blocks:
                continue
            
            page_width = page_blocks[0]['page_width']
            
            # Check positioning
            for block in page_blocks:
                center_x = (block['x0'] + block['x1']) / 2
                page_center = page_width / 2
                
                # Centered
                if abs(center_x - page_center) < page_width * 0.15:
                    layout['centered'].append(block)
                
                # Left aligned
                elif block['x0'] < page_width * 0.2:
                    layout['left_side'].append(block)
                
                # Right aligned
                elif block['x1'] > page_width * 0.8:
                    layout['right_side'].append(block)
                
                # Top of page
                if block['y0'] < 150:
                    layout['top_of_page'].append(block)
            
            # Find isolated blocks
            for block in page_blocks:
                nearby = 0
                for other in page_blocks:
                    if (other != block and 
                        abs(other['y0'] - block['y0']) < 30):
                        nearby += 1
                
                if nearby <= 1:
                    layout['isolated'].append(block)
        
        return layout
    
    def _find_title(self, blocks: List[Dict[str, Any]], 
                   structure: Dict[str, Any], language: str) -> str:
        """Try to find the document title."""
        if not blocks:
            return ""
        
        # Look on first page
        first_page = [b for b in blocks if b['page'] == 0]
        if not first_page:
            return ""
        
        candidates = []
        
        for block in first_page:
            score = self._score_title_candidate(block, structure, language)
            if score > 0.3:  
                candidates.append((block, score))
        
        if not candidates:
            # Just pick the biggest font that's not obviously wrong
            valid = [b for b in first_page 
                    if not self._obviously_not_title(b['text'], language)]
            if valid:
                best = max(valid, key=lambda x: x['font_size'])
                return self._clean_title(best['text'], language)
            return ""
        
        # Pick the highest scoring one
        best = max(candidates, key=lambda x: x[1])[0]
        return self._clean_title(best['text'], language)
    
    def _score_title_candidate(self, block: Dict[str, Any], 
                              structure: Dict[str, Any], language: str) -> float:
        """Give a score to how likely this block is to be the title."""
        score = 0.0
        text = block['text'].strip()
        
        # Font size
        fonts = structure.get('fonts', {})
        if fonts:
            if block['font_size'] >= fonts.get('p95', 14):
                score += 0.3
            elif block['font_size'] >= fonts.get('p90', 13):
                score += 0.2
        
        # Bold text
        if self._is_bold(block):
            score += 0.25
        
        # Position
        layout = structure.get('layout', {})
        if block in layout.get('centered', []):
            score += 0.2
        if block in layout.get('top_of_page', []):
            score += 0.15
        
        # Length
        script = block.get('script_type', 'latin')
        if script == 'cjk':
            # Character count for Asian languages
            if 5 <= len(text) <= 50:
                score += 0.1
        else:
            # Word count for others
            words = len(text.split())
            if 3 <= words <= 25:
                score += 0.1
            elif words > 30:
                score -= 0.3
        
        # Overall length
        if 10 <= len(text) <= 200:
            score += 0.05
        
        # Check if obviously wrong
        if self._obviously_not_title(text, language):
            score = 0.0
        
        return score
    
    def _build_outline(self, blocks: List[Dict[str, Any]], 
                      structure: Dict[str, Any], title: str, 
                      language: str) -> List[Dict[str, Any]]:
        """Build the document outline by finding headings."""
        if not blocks:
            return []
        
        # Score potential headings
        candidates = []
        
        for block in blocks:
            score = self._score_heading_candidate(block, structure, language)
            if score > 0.4:  
                candidates.append((block, score))
        
        if not candidates:
            return []
        
        # Remove title matches
        if title:
            candidates = self._remove_title_matches(candidates, title)
        
        # Filter to valid headings
        valid_headings = []
        for block, score in candidates:
            if self._is_valid_heading(block, language):
                valid_headings.append(block)
        
        if not valid_headings:
            return []
        
        # Assign heading levels
        self._assign_levels(valid_headings, structure, language)
        
        # Sort by page and position
        valid_headings.sort(key=lambda h: (h['page'], h['y0']))
        
        # Format output
        return self._format_headings(valid_headings)
    
    def _score_heading_candidate(self, block: Dict[str, Any], 
                                structure: Dict[str, Any], language: str) -> float:
        """Score how likely a block is to be a heading."""
        score = 0.0
        text = block['text'].strip()
        script = block.get('script_type', 'latin')
        
        # Font size
        fonts = structure.get('fonts', {})
        if fonts:
            if block['font_size'] >= fonts.get('p90', 13):
                score += 0.2
            elif block['font_size'] >= fonts.get('p75', 12):
                score += 0.15
        
        # Bold
        if self._is_bold(block):
            score += 0.25
        
        # Content patterns
        content = structure.get('content', {})
        
        if block in content.get('numbered_items', []):
            score += 0.35
        
        if block in content.get('keywords', []):
            score += 0.3
        
        if block in content.get('caps_text', []):
            score += 0.2
        
        if block in content.get('colon_endings', []):
            score += 0.25
        
        # Layout
        layout = structure.get('layout', {})
        
        if block in layout.get('centered', []):
            score += 0.15
        
        if block in layout.get('isolated', []):
            score += 0.2
        
        # Length factors
        if script == 'cjk':
            # Character count
            if 3 <= len(text) <= 30:
                score += 0.1
            elif len(text) > 50:
                score -= 0.4
        else:
            # Word count
            words = len(text.split())
            if 2 <= words <= 15:
                score += 0.1
            elif words > 25:
                score -= 0.4
        
        # Check if definitely not a heading
        if self._definitely_not_heading(text, language):
            score = 0.0
        
        return score
    
    def _assign_levels(self, headings: List[Dict[str, Any]], 
                      structure: Dict[str, Any], language: str) -> None:
        """Assign H1, H2, H3 levels to headings."""
        if not headings:
            return
        
        for heading in headings:
            text = heading['text'].strip()
            text_lower = text.lower()
            script = heading.get('script_type', 'latin')
            level = "H3"  # Default
            
            # H1 - major sections
            if self._is_major_section(text_lower, heading, language):
                level = "H1"
            
            # H2 - subsections
            elif self._is_subsection(text_lower, heading, language):
                level = "H2"
            
            heading['level'] = level
    
    def _is_major_section(self, text_lower: str, heading: Dict[str, Any], 
                         language: str) -> bool:
        """Check if this is a major section heading."""
        # Look for major keywords
        major_words = []
        for script_family, languages in self.lang_keywords.items():
            if language in languages:
                words = languages[language]
                # Filter for major section words
                major_words = [w for w in words if any(m in w for m in 
                    ['introduction', 'overview', 'summary', 'background', 'conclusion',
                     'methodology', 'results', 'discussion', 'references', 'appendix',
                     'abstract', 'introducción', 'resumen', 'conclusión',
                     'введение', 'заключение', 'مقدمة', 'خاتمة', '引言', '结论'])]
                break
        
        # Use English as fallback
        if not major_words:
            major_words = ['introduction', 'overview', 'background', 'summary', 
                          'conclusion', 'methodology', 'results', 'discussion',
                          'references', 'appendix', 'acknowledgments', 'abstract']
        
        # Check for keywords
        if any(word in text_lower for word in major_words):
            return True
        
        # Check numbering
        script = heading.get('script_type', 'latin')
        if script == 'cjk':
            # Asian numbering
            if re.match(r'^[一二三四五六七八九十\d]+[、.]?\s*', heading['text']):
                return True
        else:
            # Western numbering
            if re.match(r'^\d+\.?\s+[A-Za-z\u0400-\u04FF\u0600-\u06FF]', heading['text']):
                return True
        
        # Large font on early pages
        if (heading['page'] <= 1 and 
            self._is_bold(heading) and 
            heading['font_size'] >= 14):
            return True
        
        return False
    
    def _is_subsection(self, text_lower: str, heading: Dict[str, Any], 
                      language: str) -> bool:
        """Check if this is a subsection heading."""
        # Look for subsection keywords
        sub_words = []
        for script_family, languages in self.lang_keywords.items():
            if language in languages:
                words = languages[language]
                # Filter for subsection words
                sub_words = [w for w in words if any(s in w for s in 
                    ['objectives', 'goals', 'requirements', 'specifications', 'timeline',
                     'approach', 'evaluation', 'criteria', 'milestones', 'objetivos',
                     'цели', 'требования', 'أهداف', 'متطلبات', '目标', '要求'])]
                break
        
        # English fallback
        if not sub_words:
            sub_words = ['objectives', 'goals', 'requirements', 'specifications',
                        'timeline', 'approach', 'evaluation', 'criteria',
                        'milestones', 'deliverables', 'scope', 'limitations']
        
        # Check keywords
        if any(word in text_lower for word in sub_words):
            return True
        
        # Colon endings
        script = heading.get('script_type', 'latin')
        if self._ends_with_colon(heading['text'], script):
            return True
        
        # Sub-numbering
        if re.match(r'^\d+\.\d+\.?\s+[A-Za-z\u0400-\u04FF\u0600-\u06FF]', heading['text']):
            return True
        
        return False
    
    def _obviously_not_title(self, text: str, language: str) -> bool:
        """Check if text is obviously not a title."""
        text_lower = text.lower()
        
        # URLs and emails
        if any(p in text_lower for p in ['www.', 'http', '@', '.com', '.org']):
            return True
        
        # Too short
        if len(text.strip()) < 3:
            return True
        
        # Date patterns for Western languages
        if language in ['english', 'spanish', 'french', 'german']:
            if re.match(r'^(january|february|march|april|may|june|july|august|september|october|november|december|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+\d{1,2},?\s+\d{4}', text_lower):
                return True
        
        return False
    
    def _definitely_not_heading(self, text: str, language: str) -> bool:
        """Check if text is definitely not a heading."""
        text_lower = text.lower()
        
        # Administrative text
        admin_terms = [
            'office use only', 'signature', 'date', 'remarks',
            'faxed to:', 'e-mailed', 'mailed', 'couriered'
        ]
        
        if any(term in text_lower for term in admin_terms):
            return True
        
        # Too long
        script = self._get_script_type(text)
        if script == 'cjk':
            if len(text) > 100:  # Characters for Asian languages
                return True
        else:
            if len(text.split()) > 30:  # Words for others
                return True
        
        # Mostly non-text
        useful_chars = sum(1 for c in text if c.isalnum() or ord(c) > 127)
        if useful_chars < len(text) * 0.4:
            return True
        
        return False
    
    def _is_valid_heading(self, block: Dict[str, Any], language: str) -> bool:
        """Final check if a block can be a heading."""
        text = block['text'].strip()
        script = block.get('script_type', 'latin')
        
        # Length limits
        if script == 'cjk':
            if not (2 <= len(text) <= 80):
                return False
        else:
            if not (5 <= len(text) <= 250):
                return False
                
            # Word limit for non-Asian
            if len(text.split()) > 25:
                return False
        
        # Must not be definitely wrong
        if self._definitely_not_heading(text, language):
            return False
        
        return True
    
    def _is_bold(self, block: Dict[str, Any]) -> bool:
        """Check if text uses bold formatting."""
        return bool(block['flags'] & 2**4)
    
    def _clean_title(self, title: str, language: str) -> str:
        """Clean up the title text."""
        # Fix Unicode
        title = unicodedata.normalize('NFC', title.strip())
        
        # Fix whitespace
        title = re.sub(r'\s+', ' ', title)
        
        # Length limits by script
        script = self._get_script_type(title)
        if script == 'cjk':
            # Character limit for Asian languages
            if len(title) > 100:
                title = title[:100] + "..."
        else:
            # Word limit for others
            if len(title) > 200:
                words = title.split()
                if len(words) > 30:
                    title = ' '.join(words[:30]) + "..."
        
        return title
    
    def _remove_title_matches(self, candidates: List[Tuple], 
                             title: str) -> List[Tuple]:
        """Remove candidates that are too similar to the title."""
        if not title:
            return candidates
        
        # Normalize for comparison
        title_clean = unicodedata.normalize('NFC', title.lower())
        title_words = set(title_clean.split())
        
        filtered = []
        
        for block, score in candidates:
            block_clean = unicodedata.normalize('NFC', block['text'].lower())
            block_words = set(block_clean.split())
            
            if title_words and block_words:
                overlap = len(title_words.intersection(block_words))
                similarity = overlap / max(len(title_words), len(block_words))
                
                # Keep if less than 40% similar
                if similarity < 0.4:
                    filtered.append((block, score))
            else:
                filtered.append((block, score))
        
        return filtered
    
    def _format_headings(self, headings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format headings for JSON output."""
        outline = []
        
        for heading in headings:
            # Clean up Unicode
            text = unicodedata.normalize('NFC', heading['text'].strip())
            
            outline.append({
                "level": heading.get('level', 'H3'),
                "text": text,
                "page": heading['page']
            })
        
        return outline
    
    def save_output(self, result: Dict[str, Any], output_path: str) -> None:
        """Save results to JSON file."""
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=4, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Error saving to {output_path}: {e}")

def process_all_pdfs() -> None:
    """Process all PDF files in the input directory."""
    input_dir = Path("/app/input")
    output_dir = Path("/app/output")
    
    # Make sure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not input_dir.exists():
        print("Input directory /app/input not found")
        return
    
    # Set up the extractor
    extractor = MultilingualPDFExtractor()
    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in /app/input")
        return
    
    print(f"Found {len(pdf_files)} PDF files to process...")
    
    # Process each file
    for pdf_file in pdf_files:
        try:
            print(f"Processing {pdf_file.name}...")
            
            # Extract the structure
            result = extractor.extract_structure(str(pdf_file))
            
            # Save with matching filename
            output_file = output_dir / f"{pdf_file.stem}.json"
            extractor.save_output(result, str(output_file))
            
            print(f"✓ Completed: {output_file.name}")
            
        except Exception as e:
            print(f"✗ Failed: {pdf_file.name} - {e}")
            logger.error(f"Processing failed for {pdf_file.name}: {e}")

def main() -> None:
    """Main entry point."""
    try:
        process_all_pdfs()
        print("All files processed successfully!")
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()