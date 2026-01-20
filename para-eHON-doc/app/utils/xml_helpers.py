"""
XML Helper Functions
====================
Utilities for XML escaping and text manipulation.
"""
import re


def escape_xml(text: str) -> str:
    """Escape special XML characters and fix encoding issues."""
    if not text:
        return ""
    text = str(text)
    text = text.replace("Â£", "£")
    text = text.replace("â€™", "'")
    text = text.replace("â€œ", '"')
    text = text.replace("â€", '"')
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    return text



def smart_sentence_split(text: str) -> list:
    """
    Split text into sentences without breaking on decimal numbers.
    Protects digit.digit patterns and common abbreviations.
    """
    if not text:
        return []
    
    protected = text
    
    # Protect decimal numbers: 1.2, 4.29, £3.7, etc.
    protected = re.sub(r'(\d+)\.(\d+)', r'\1<DEC>\2', protected)
    
    # Protect common abbreviations
    for abbr in ['e.g.', 'i.e.', 'vs.', 'etc.']:
        protected = protected.replace(abbr, abbr.replace('.', '<DEC>'))
    
    # Split on: period + space + capital letter
    sentences = re.split(r'\.\s+(?=[A-Z])', protected)
    
    # Restore and clean up
    result = []
    for s in sentences:
        s = s.replace('<DEC>', '.').strip()
        if s:
            if not s.endswith('.'):
                s += '.'
            result.append(s)
    
    return result