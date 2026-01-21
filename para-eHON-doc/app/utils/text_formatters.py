import re
from .xml_helpers import escape_xml, smart_sentence_split

def format_as_bullets(text: str, font_name: str = "Arial") -> str:
    """
    Format soft notes text as bullet points, each sentence on a new line.
    Uses smart sentence splitting that handles 99% of edge cases.
    """
    if not text or text == "No notes available.":
        return text
    
    # Use smart sentence splitting
    sentences = smart_sentence_split(text)
    
    if not sentences:
        return escape_xml(text)
    
    # Ensure each sentence ends with proper punctuation
    cleaned_sentences = []
    for s in sentences:
        s = s.strip()
        if s and not s.endswith(('.', '!', '?', '"', "'")):
            s += '.'
        if s:
            cleaned_sentences.append(s)
    
    if not cleaned_sentences:
        return escape_xml(text)
    
    bullet_char = "•"
    
    # First bullet (without line break)
    result = (
        f'</w:t></w:r>'
        f'<w:r><w:rPr><w:rFonts w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="{font_name}"/></w:rPr>'
        f'<w:t>{bullet_char} {escape_xml(cleaned_sentences[0])}'
    )
    
    # Remaining bullets with line breaks (<w:br/>)
    for sentence in cleaned_sentences[1:]:
        result += (
            f'</w:t></w:r>'
            f'<w:r><w:rPr><w:rFonts w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="{font_name}"/></w:rPr>'
            f'<w:br/><w:t>{bullet_char} {escape_xml(sentence)}'
        )
    
    # Close the last run
    result += '</w:t></w:r><w:r><w:t>'
    
    return result


def format_as_newlines(text: str, font_name: str = "Arial") -> str:
    """Clean up text by removing * bullets and ** markdown."""
    if not text or text == "Not Available":
        return text
    
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    if not lines:
        return escape_xml(text)
    
    cleaned_lines = []
    for line in lines:
        cleaned = re.sub(r'^\s*\*\s*', '', line).strip()
        cleaned = cleaned.replace('**', '')
        if cleaned:
            cleaned_lines.append(cleaned)
    
    if not cleaned_lines:
        return escape_xml(text)
    
    result = (
        f'</w:t></w:r>'
        f'<w:r><w:rPr><w:rFonts w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="{font_name}"/></w:rPr>'
        f'<w:t>'
    ) + escape_xml(cleaned_lines[0])
    
    for line in cleaned_lines[1:]:
        result += (
            f'</w:t></w:r>'
            f'<w:r><w:rPr><w:rFonts w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="{font_name}"/></w:rPr>'
            f'<w:br/><w:t>'
        ) + escape_xml(line)
    
    result += '</w:t></w:r><w:r><w:t>'
    
    return result


def format_as_newlines_with_bold(text: str, bold_phrases: list, font_name: str = "Arial") -> str:
    """Format text with bold phrases."""
    if not text or text == "Not Available":
        return text
    
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    if not lines:
        return escape_xml(text)
    
    cleaned_lines = []
    for line in lines:
        cleaned = re.sub(r'^\s*\*\s*', '', line).strip()
        cleaned = cleaned.replace('**', '')
        if cleaned:
            cleaned_lines.append(cleaned)
    
    if not cleaned_lines:
        return escape_xml(text)
    
    def apply_bold_to_line(line: str, phrases: list) -> str:
        if not phrases:
            return escape_xml(line)
        
        sorted_phrases = sorted(phrases, key=len, reverse=True)
        
        matches = []
        for phrase in sorted_phrases:
            start = 0
            while True:
                idx = line.find(phrase, start)
                if idx == -1:
                    break
                is_covered = False
                for existing_start, existing_end, _ in matches:
                    if idx >= existing_start and idx < existing_end:
                        is_covered = True
                        break
                if not is_covered:
                    matches.append((idx, idx + len(phrase), phrase))
                start = idx + 1
        
        if not matches:
            return escape_xml(line)
        
        matches.sort(key=lambda x: x[0])
        
        result_parts = []
        last_end = 0
        
        for start, end, phrase in matches:
            if start > last_end:
                before_text = line[last_end:start]
                result_parts.append(escape_xml(before_text))
            
            escaped_phrase = escape_xml(phrase)
            bold_xml = (
                f'</w:t></w:r>'
                f'<w:r><w:rPr><w:rFonts w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="{font_name}"/><w:b/></w:rPr>'
                f'<w:t>{escaped_phrase}</w:t></w:r>'
                f'<w:r><w:rPr><w:rFonts w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="{font_name}"/></w:rPr><w:t>'
            )
            result_parts.append(bold_xml)
            
            last_end = end
        
        if last_end < len(line):
            result_parts.append(escape_xml(line[last_end:]))
        
        return ''.join(result_parts)
    
    result = apply_bold_to_line(cleaned_lines[0], bold_phrases)
    
    for line in cleaned_lines[1:]:
        result += '</w:t><w:br/><w:t>' + apply_bold_to_line(line, bold_phrases)
    
    return result


def format_vulnerability_soft_notes(text: str, font_name: str = "Arial") -> str:
    """Format Vulnerability Soft Notes with categorized bullet points."""
    if not text or text == "No notes available.":
        return text
    
    bold_categories = [
        "Health Vulnerabilities",
        "Life Event Vulnerabilities",
        "Capability Vulnerabilities"
    ]
    
    cleaned_text = text.replace("**", "")
    pattern = r'(' + '|'.join(re.escape(cat) for cat in bold_categories) + r')\s*:\s*'
    parts = re.split(pattern, cleaned_text)
    
    result_parts = []
    bullet_char = "•"
    is_first = True
    
    i = 0
    while i < len(parts):
        part = parts[i].strip()
        
        if part in bold_categories:
            content = parts[i + 1].strip() if i + 1 < len(parts) else ""
            
            if not is_first:
                result_parts.append(
                    f'<w:r><w:rPr><w:rFonts w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="{font_name}"/></w:rPr>'
                    f'<w:br/><w:br/></w:r>'
                )
            else:
                result_parts.append('</w:t></w:r>')
            
            is_first = False
            
            category_xml = (
                f'<w:r><w:rPr><w:rFonts w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="{font_name}"/><w:b/></w:rPr>'
                f'<w:t>{escape_xml(part)}:</w:t></w:r>'
            )
            result_parts.append(category_xml)
            
            if content:
                sentences = [s.strip() for s in content.split('.') if s.strip()]
                
                for sentence in sentences:
                    if not sentence:
                        continue
                    
                    bullet_xml = (
                        f'<w:r><w:rPr><w:rFonts w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="{font_name}"/></w:rPr>'
                        f'<w:br/><w:t xml:space="preserve">{bullet_char} {escape_xml(sentence)}.</w:t></w:r>'
                    )
                    result_parts.append(bullet_xml)
            
            i += 2
        else:
            i += 1
    
    if not result_parts:
        return format_as_bullets(text, font_name)
    
    final_result = ''.join(result_parts) + '<w:r><w:t>'
    
    return final_result