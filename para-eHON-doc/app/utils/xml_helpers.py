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
    Smart sentence splitter that handles edge cases:
    - Decimal numbers: £1.7 million, 3.2%, 4.5
    - Abbreviations: Dr., Mr., Mrs., Ms., Prof., etc.
    - Acronyms: U.S., U.K., e.g., i.e., etc.
    - Titles: Sr., Jr., Ltd., Inc., Co.
    - Time/dates: 3.30pm, Jan. 15
    - Ellipsis: ...
    - And more
    """
    if not text:
        return []
    
    # Step 1: Protect known patterns by replacing with placeholders
    protected = text
    replacements = []
    
    # Common abbreviations and titles (with period)
    abbreviations = [
        # Titles
        r'\bMr\.',
        r'\bMrs\.',
        r'\bMs\.',
        r'\bDr\.',
        r'\bProf\.',
        r'\bSr\.',
        r'\bJr\.',
        r'\bRev\.',
        r'\bGen\.',
        r'\bCol\.',
        r'\bLt\.',
        r'\bSgt\.',
        r'\bCapt\.',
        r'\bAdm\.',
        # Business
        r'\bLtd\.',
        r'\bInc\.',
        r'\bCo\.',
        r'\bCorp\.',
        r'\bPlc\.',
        r'\bLLP\.',
        r'\bLLC\.',
        # Latin/common
        r'\be\.g\.',
        r'\bi\.e\.',
        r'\betc\.',
        r'\bvs\.',
        r'\bv\.',
        r'\bcf\.',
        r'\bviz\.',
        r'\bapprox\.',
        r'\best\.',
        r'\bmin\.',
        r'\bmax\.',
        r'\bavg\.',
        r'\bno\.',
        r'\bNo\.',
        r'\bvol\.',
        r'\bVol\.',
        r'\bpp\.',
        r'\bpg\.',
        r'\bfig\.',
        r'\bFig\.',
        # Months
        r'\bJan\.',
        r'\bFeb\.',
        r'\bMar\.',
        r'\bApr\.',
        r'\bJun\.',
        r'\bJul\.',
        r'\bAug\.',
        r'\bSep\.',
        r'\bSept\.',
        r'\bOct\.',
        r'\bNov\.',
        r'\bDec\.',
        # Geography/addresses
        r'\bSt\.',
        r'\bAve\.',
        r'\bRd\.',
        r'\bBlvd\.',
        r'\bDr\.',
        r'\bCt\.',
        r'\bPl\.',
        r'\bMt\.',
        r'\bFt\.',
        # Countries/regions
        r'\bU\.S\.',
        r'\bU\.K\.',
        r'\bU\.S\.A\.',
        r'\bE\.U\.',
        # Academic
        r'\bPh\.D\.',
        r'\bM\.D\.',
        r'\bB\.A\.',
        r'\bM\.A\.',
        r'\bB\.Sc\.',
        r'\bM\.Sc\.',
        r'\bM\.B\.A\.',
    ]
    
    # Replace abbreviations with placeholders
    placeholder_counter = 0
    for abbrev_pattern in abbreviations:
        matches = list(re.finditer(abbrev_pattern, protected, re.IGNORECASE))
        for match in reversed(matches):  # Reverse to maintain positions
            placeholder = f"__ABBREV_{placeholder_counter}__"
            replacements.append((placeholder, match.group()))
            protected = protected[:match.start()] + placeholder + protected[match.end():]
            placeholder_counter += 1
    
    # Protect decimal numbers (£1.7, 3.2%, 0.5, etc.)
    # Pattern: digit(s) + period + digit(s)
    decimal_pattern = r'(\d+\.\d+)'
    matches = list(re.finditer(decimal_pattern, protected))
    for match in reversed(matches):
        placeholder = f"__DECIMAL_{placeholder_counter}__"
        replacements.append((placeholder, match.group()))
        protected = protected[:match.start()] + placeholder + protected[match.end():]
        placeholder_counter += 1
    
    # Protect ellipsis (...)
    ellipsis_pattern = r'\.{2,}'
    matches = list(re.finditer(ellipsis_pattern, protected))
    for match in reversed(matches):
        placeholder = f"__ELLIPSIS_{placeholder_counter}__"
        replacements.append((placeholder, match.group()))
        protected = protected[:match.start()] + placeholder + protected[match.end():]
        placeholder_counter += 1
    
    # Protect quoted sentences ending with period inside quotes
    # Pattern: "text." or 'text.'
    quote_pattern = r'(["\'][^"\']*\.["\'])'
    matches = list(re.finditer(quote_pattern, protected))
    for match in reversed(matches):
        placeholder = f"__QUOTE_{placeholder_counter}__"
        replacements.append((placeholder, match.group()))
        protected = protected[:match.start()] + placeholder + protected[match.end():]
        placeholder_counter += 1
    
    # Protect time formats (3.30pm, 10.15am)
    time_pattern = r'(\d{1,2}\.\d{2}\s*(?:am|pm|AM|PM))'
    matches = list(re.finditer(time_pattern, protected))
    for match in reversed(matches):
        placeholder = f"__TIME_{placeholder_counter}__"
        replacements.append((placeholder, match.group()))
        protected = protected[:match.start()] + placeholder + protected[match.end():]
        placeholder_counter += 1
    
    # Protect version numbers (v1.0, version 2.5)
    version_pattern = r'(v(?:ersion)?\s*\d+\.\d+)'
    matches = list(re.finditer(version_pattern, protected, re.IGNORECASE))
    for match in reversed(matches):
        placeholder = f"__VERSION_{placeholder_counter}__"
        replacements.append((placeholder, match.group()))
        protected = protected[:match.start()] + placeholder + protected[match.end():]
        placeholder_counter += 1
    
    # Step 2: Now split on sentence boundaries
    # Sentence boundary: period/exclamation/question + space(s) + capital letter
    sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])'
    sentences = re.split(sentence_pattern, protected)
    
    # Step 3: Restore placeholders in each sentence
    restored_sentences = []
    for sentence in sentences:
        restored = sentence
        for placeholder, original in replacements:
            restored = restored.replace(placeholder, original)
        restored = restored.strip()
        if restored:
            restored_sentences.append(restored)
    
    return restored_sentences