"""
PDF Service
===========
Handles PDF generation from JSON data using templates.
"""
import os
import re
import json
import shutil
import tempfile
import zipfile
import subprocess
from typing import Dict, List, Optional
from datetime import datetime

from app.config import settings, TEMPLATE_MAPPING
from app.utils import (
    escape_xml,
    format_as_bullets,
    format_as_newlines,
    format_as_newlines_with_bold,
    format_vulnerability_soft_notes
)


class PDFService:
    """Service for generating PDFs from extracted data."""
    
    def load_json_file(self, file_path: str) -> dict:
        """Load a JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def convert_docx_to_pdf(self, docx_path: str, output_pdf_path: str) -> bool:
        """Convert a DOCX file to PDF using LibreOffice."""
        try:
            output_dir = os.path.dirname(output_pdf_path)
            subprocess.run([
                'libreoffice', '--headless', '--convert-to', 'pdf',
                '--outdir', output_dir, docx_path
            ], check=True)
            # Rename the output file
            base_name = os.path.splitext(os.path.basename(docx_path))[0]
            generated_pdf = os.path.join(output_dir, f"{base_name}.pdf")
            if generated_pdf != output_pdf_path:
                shutil.move(generated_pdf, output_pdf_path)
            print(f"  Converted to PDF: {output_pdf_path}")
            return True
        except Exception as e:
            print(f"  Error converting to PDF with LibreOffice: {e}")
            return False
    
    def fix_fonts(self,unpacked_dir: str, font_name: str = "Arial"):
        """
        Replace all fonts with a universal font and fix text alignment.
        """
        
        def process_xml_file(file_path: str):
            """Process a single XML file to replace all font declarations."""
            if not os.path.exists(file_path):
                return False
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 1. Replace all w:rFonts declarations (self-closing)
            content = re.sub(
                r'<w:rFonts[^>]*/>', 
                f'<w:rFonts w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="{font_name}" w:eastAsia="{font_name}"/>', 
                content
            )
            
            # 2. Replace w:rFonts with content (non-self-closing)
            content = re.sub(
                r'<w:rFonts[^>]*>.*?</w:rFonts>', 
                f'<w:rFonts w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="{font_name}" w:eastAsia="{font_name}"/>', 
                content,
                flags=re.DOTALL
            )
            
            # 3. Remove theme fonts
            content = re.sub(r'\s*w:asciiTheme="[^"]*"', '', content)
            content = re.sub(r'\s*w:hAnsiTheme="[^"]*"', '', content)
            content = re.sub(r'\s*w:cstheme="[^"]*"', '', content)
            content = re.sub(r'\s*w:eastAsiaTheme="[^"]*"', '', content)
            
            # =====================================================================
            # 4. FIX ALL JUSTIFICATION - AGGRESSIVE APPROACH
            # =====================================================================
            
            # 4a. Replace w:jc with val="both" (justified) -> "left" (all variations)
            content = re.sub(r'<w:jc\s+w:val\s*=\s*"both"\s*/>', '<w:jc w:val="left"/>', content)
            content = re.sub(r'<w:jc\s+w:val\s*=\s*"both"\s*>', '<w:jc w:val="left">', content)
            content = re.sub(r'<w:jc\s+w:val\s*=\s*\'both\'\s*/>', '<w:jc w:val="left"/>', content)
            content = re.sub(r'<w:jc\s+w:val\s*=\s*\'both\'\s*>', '<w:jc w:val="left">', content)
            
            # 4b. Catch ANY remaining "both" value in w:jc tags (nuclear option)
            content = re.sub(r'(<w:jc[^>]*w:val\s*=\s*["\'])both(["\'][^>]*>)', r'\1left\2', content)
            content = re.sub(r'(<w:jc[^>]*w:val\s*=\s*["\'])both(["\'][^>]*/\s*>)', r'\1left\2', content)
            
            # 4c. Handle distribute alignment (another form of justify)
            content = re.sub(r'(<w:jc[^>]*w:val\s*=\s*["\'])distribute(["\'][^>]*>)', r'\1left\2', content)
            content = re.sub(r'(<w:jc[^>]*w:val\s*=\s*["\'])distribute(["\'][^>]*/\s*>)', r'\1left\2', content)
            
            # 4d. Fix table cell vertical alignment issues that can cause stretching
            # Replace "distribute" in table properties
            content = re.sub(r'(<w:vAlign[^>]*w:val\s*=\s*["\'])both(["\'][^>]*>)', r'\1top\2', content)
            content = re.sub(r'(<w:vAlign[^>]*w:val\s*=\s*["\'])distribute(["\'][^>]*>)', r'\1top\2', content)
            
            # 4e. ULTIMATE FALLBACK - Replace literal string "both" in any w:jc context
            # This regex finds <w:jc ...> tags and replaces "both" with "left" inside them
            def replace_both_in_jc(match):
                return match.group(0).replace('"both"', '"left"').replace("'both'", "'left'")
            
            content = re.sub(r'<w:jc[^>]*>', replace_both_in_jc, content)
            
            # =====================================================================
            # 5. FIX PARAGRAPH PROPERTIES IN STYLES
            # =====================================================================
            
            # Fix default paragraph justification in style definitions
            # This catches cases where justification is inherited from styles
            def fix_pPr_justification(match):
                pPr_content = match.group(0)
                # Replace both with left inside paragraph properties
                pPr_content = re.sub(r'"both"', '"left"', pPr_content)
                pPr_content = re.sub(r"'both'", "'left'", pPr_content)
                return pPr_content
            
            content = re.sub(r'<w:pPr>.*?</w:pPr>', fix_pPr_justification, content, flags=re.DOTALL)
            content = re.sub(r'<w:pPrDefault>.*?</w:pPrDefault>', fix_pPr_justification, content, flags=re.DOTALL)
            
            # =====================================================================
            # 6. FIX TABLE STYLES
            # =====================================================================
            
            # Fix justification in table styles
            def fix_tblPr_justification(match):
                tbl_content = match.group(0)
                tbl_content = re.sub(r'"both"', '"left"', tbl_content)
                tbl_content = re.sub(r"'both'", "'left'", tbl_content)
                return tbl_content
            
            content = re.sub(r'<w:tblPr>.*?</w:tblPr>', fix_tblPr_justification, content, flags=re.DOTALL)
            content = re.sub(r'<w:tcPr>.*?</w:tcPr>', fix_tblPr_justification, content, flags=re.DOTALL)
            content = re.sub(r'<w:trPr>.*?</w:trPr>', fix_tblPr_justification, content, flags=re.DOTALL)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        # Process document.xml
        doc_path = os.path.join(unpacked_dir, 'word', 'document.xml')
        process_xml_file(doc_path)
        
        # Process styles.xml (CRITICAL - this is where default styles live)
        styles_path = os.path.join(unpacked_dir, 'word', 'styles.xml')
        process_xml_file(styles_path)
        
        # Process numbering.xml (can have paragraph properties)
        numbering_path = os.path.join(unpacked_dir, 'word', 'numbering.xml')
        process_xml_file(numbering_path)
        
        # Process settings.xml
        settings_path = os.path.join(unpacked_dir, 'word', 'settings.xml')
        process_xml_file(settings_path)
        
        # Process header/footer files
        word_dir = os.path.join(unpacked_dir, 'word')
        if os.path.exists(word_dir):
            for filename in os.listdir(word_dir):
                if filename.startswith('header') and filename.endswith('.xml'):
                    process_xml_file(os.path.join(word_dir, filename))
                if filename.startswith('footer') and filename.endswith('.xml'):
                    process_xml_file(os.path.join(word_dir, filename))
        
        # Process theme
        theme_path = os.path.join(unpacked_dir, 'word', 'theme', 'theme1.xml')
        if os.path.exists(theme_path):
            with open(theme_path, 'r', encoding='utf-8') as f:
                theme_content = f.read()
            
            theme_content = re.sub(r'<a:latin typeface="[^"]*"', f'<a:latin typeface="{font_name}"', theme_content)
            theme_content = re.sub(r'<a:ea typeface="[^"]*"', f'<a:ea typeface="{font_name}"', theme_content)
            theme_content = re.sub(r'<a:cs typeface="[^"]*"', f'<a:cs typeface="{font_name}"', theme_content)
            
            with open(theme_path, 'w', encoding='utf-8') as f:
                f.write(theme_content)
        
        print(f"  âœ“ Fonts standardized to {font_name}")
        print(f"  âœ“ ALL text alignment forced to LEFT (justify disabled everywhere)")
    
    def get_value_from_json(self, data: dict, section_key: str, field_name: str) -> str:
        """Get a value from the JSON data using section key and field name."""
        section_data = data.get(section_key, {})
        if not section_data:
            return "Not Available"
        
        value = section_data.get(field_name, "Not Available")
        return value if value else "Not Available"
    
    def get_soft_notes(self, data: dict, section_key: str, soft_notes_field: str) -> str:
        """Get soft notes for a section."""
        value = self.get_value_from_json(data, section_key, soft_notes_field)
        
        empty_values = ["not available", "not found", "na", "n a", "none", "null", ""]
        
        if not value:
            return "No notes available."
        
        normalized = re.sub(r'[^a-z0-9\s]', '', str(value).lower()).strip()
        
        if normalized in empty_values:
            return "No notes available."
        
        return value
    
    
    def is_valid_value(self, value) -> bool:
        """Check if a value is valid (not empty/not found/not available)."""
        if not value:
            return False
        
        empty_values = ["not available", "not found", "na", "n a", "none", "null", ""]
        normalized = re.sub(r'[^a-z0-9\s]', '', str(value).lower()).strip()
        
        return normalized not in empty_values


    def get_combined_soft_notes(self, data: dict, section_key: str, field1: str, field2: str) -> str:
        """Combine two soft notes fields (for Income & Expenditure)."""
        section_data = data.get(section_key, {})
        if not section_data:
            return "No notes available."
        
        value1 = section_data.get(field1, "")
        value2 = section_data.get(field2, "")
        
        parts = []
        
        if value1 and self.is_valid_value(value1):
            label1 = field1.replace(" Soft Notes", "")
            parts.append(f"{label1}: {value1}")
        
        if value2 and self.is_valid_value(value2):
            label2 = field2.replace(" Soft Notes", "")
            parts.append(f"{label2}: {value2}")
        
        if not parts:
            return "No notes available."
        
        return "\n\n".join(parts)


    def get_array_formatted_dynamic(self, data: dict, section_key: str, array_field: str, font_name: str = "Arial") -> str:
        """
        Dynamically format array items (Assets, Products, Goals) for PDF.
        Reads ALL fields from each array item - excludes Soft Notes fields.
        """
        section_data = data.get(section_key, {})
        if not section_data:
            return ""
        
        array_data = section_data.get(array_field, [])
        if not array_data or not isinstance(array_data, list):
            return ""
        
        all_items = []
        
        for idx, item in enumerate(array_data, 1):
            if not isinstance(item, dict):
                continue
            
            item_facts = []
            
            for field_name, value in item.items():
                if "Soft Notes" in field_name or "soft notes" in field_name.lower():
                    continue
                
                if not self.is_valid_value(value):
                    continue
                
                escaped_field = str(field_name).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                escaped_value = str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                
                item_facts.append(
                    f'<w:r><w:rPr><w:rFonts w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="{font_name}"/><w:b/></w:rPr>'
                    f'<w:t>{escaped_field}:</w:t></w:r>'
                    f'<w:r><w:rPr><w:rFonts w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="{font_name}"/></w:rPr>'
                    f'<w:t xml:space="preserve"> {escaped_value}</w:t></w:r>'
                )
            
            if item_facts:
                item_type = array_field.rstrip('s')  # Assets -> Asset
                
                header = (
                    f'<w:r><w:rPr><w:rFonts w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="{font_name}"/><w:b/></w:rPr>'
                    f'<w:t>{item_type} {idx}:</w:t></w:r>'
                )
                
                item_content = "<w:r><w:br/></w:r>".join(item_facts)
                all_items.append(header + "<w:r><w:br/></w:r>" + item_content)
        
        if not all_items:
            return ""
        
        return "<w:r><w:br/></w:r><w:r><w:br/></w:r>".join(all_items)


    def get_hard_facts_with_array(self, data: dict, section_key: str, hard_facts_fields: list, array_field: str = None, font_name: str = "Arial") -> str:
        """
        Get hard facts + array data combined.
        """
        section_data = data.get(section_key, {})
        print(f"\n[DEBUG 5] section_key: {section_key}")
        print(f"[DEBUG 5] section_data exists: {bool(section_data)}")
        print(f"[DEBUG 5] section_data keys: {list(section_data.keys()) if section_data else 'EMPTY'}")
        
        if not section_data:
            return "No data available."
        
        # 1. Process flat hard facts fields
        flat_facts_xml = ""
        if hard_facts_fields:
            facts = []
            for field in hard_facts_fields:
                value = section_data.get(field)
                
                if not self.is_valid_value(value):
                    continue
                
                escaped_field = str(field).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                escaped_value = str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                
                facts.append(
                    f'<w:r><w:rPr><w:rFonts w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="{font_name}"/><w:b/></w:rPr>'
                    f'<w:t>{escaped_field}:</w:t></w:r>'
                    f'<w:r><w:rPr><w:rFonts w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="{font_name}"/></w:rPr>'
                    f'<w:t xml:space="preserve"> {escaped_value}</w:t></w:r>'
                )
            
            flat_facts_xml = "<w:r><w:br/></w:r>".join(facts) if facts else ""
        
        # 2. Process array field dynamically
        array_xml = ""
        if array_field:
            array_xml = self.get_array_formatted_dynamic(data, section_key, array_field, font_name)
        
        # 3. Combine and wrap with proper XML structure
        # The placeholder is inside <w:t>...</w:t>, so we need to close it,
        # insert our content, and reopen for any trailing content
        if flat_facts_xml and array_xml:
            combined = flat_facts_xml + "<w:r><w:br/></w:r><w:r><w:br/></w:r>" + array_xml
            return f'</w:t></w:r>{combined}<w:r><w:t>'
        elif array_xml:
            return f'</w:t></w:r>{array_xml}<w:r><w:t>'
        elif flat_facts_xml:
            return f'</w:t></w:r>{flat_facts_xml}<w:r><w:t>'
        else:
            return "No data available."
        
        
    
    
    
    def get_hard_facts_formatted(self, data: dict, section_key: str, fields: list, font_name: str = "Arial") -> str:
        """Get hard facts formatted with each fact on a new line."""
        section_data = data.get(section_key, {})
        if not section_data:
            return "No data available."
        
        empty_values = ["not available", "not found", "na", "n a", "none", "null", ""]
        
        facts = []
        for field in fields:
            value = section_data.get(field)
            
            if not value:
                continue
            
            normalized = re.sub(r'[^a-z0-9\s]', '', str(value).lower()).strip()
            
            if normalized not in empty_values:
                escaped_field = str(field).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                escaped_value = str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                facts.append(
                    f'<w:r><w:rPr><w:rFonts w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="{font_name}"/><w:b/></w:rPr>'
                    f'<w:t>{escaped_field}:</w:t></w:r>'
                    f'<w:r><w:rPr><w:rFonts w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="{font_name}"/></w:rPr>'
                    f'<w:t xml:space="preserve"> {escaped_value}</w:t></w:r>'
                )
        
        if not facts:
            return "No data available."
        
        #return "<w:r><w:br/></w:r>".join(facts)
        inner_content = "<w:r><w:br/></w:r>".join(facts)
        return f'</w:t></w:r>{inner_content}<w:r><w:t>'
    
    def unpack_docx(self, docx_path: str, output_dir: str) -> bool:
        """Unpack a DOCX file to a directory."""
        try:
            os.makedirs(output_dir, exist_ok=True)
            with zipfile.ZipFile(docx_path, 'r') as zip_ref:
                zip_ref.extractall(output_dir)
            print(f"  Unpacked: {docx_path}")
            return True
        except Exception as e:
            print(f"  Error unpacking docx: {e}")
            return False
    
    def pack_docx(self, unpacked_dir: str, output_path: str) -> bool:
        """Pack a directory back into a DOCX file."""
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
            
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(unpacked_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, unpacked_dir)
                        zipf.write(file_path, arcname)
            
            print(f"  Created: {output_path}")
            return True
        except Exception as e:
            print(f"  Error packing docx: {e}")
            return False
    
    def replace_simple_placeholder(self, content: str, placeholder: str, value: str, is_hard_facts: bool = False, font_name: str = "Arial") -> str:
        """Replace a simple placeholder with a value."""
        
        first_page_placeholders = [
            "[Meeting Objective]",
            "[Client Name(s)]",
            "[Adviser Name]",
            "[Meeting Date]",
            "[Meeting Format]",
            "[Opportunity Value]",
            "[Document Generation Date]"
        ]
        
        if is_hard_facts:
            escaped_value = value
        elif placeholder in first_page_placeholders:
            escaped_value = escape_xml(value)
        else:
            escaped_text = escape_xml(value)
            escaped_value = (
                f'</w:t></w:r>'
                f'<w:r><w:rPr><w:rFonts w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="{font_name}"/></w:rPr>'
                f'<w:t xml:space="preserve">{escaped_text}</w:t></w:r>'
                f'<w:r><w:t>'
            )
        
        xml_placeholder = placeholder.replace("&", "&amp;")
        content = content.replace(placeholder, escaped_value)
        content = content.replace(xml_placeholder, escaped_value)
        return content
    
    def replace_split_placeholder(self, content: str, section_name: str, soft_notes_value: str) -> str:
        """Replace split placeholders where [SECTION Soft Notes] is split across XML runs."""
        if '</w:r>' in soft_notes_value or '<w:br/>' in soft_notes_value:
            escaped_value = soft_notes_value
        else:
            escaped_value = escape_xml(soft_notes_value)
        
        xml_section_name = section_name.replace("&", "&amp;")
        
        pattern = (
            rf'(<w:t>\[</w:t>\s*</w:r>\s*'
            rf'<w:r[^>]*>\s*<w:rPr>\s*<w:color[^/]*/>\s*<w:szCs[^/]*/>\s*</w:rPr>\s*'
            rf'<w:t>{re.escape(xml_section_name)}</w:t>\s*</w:r>\s*'
            rf'<w:r[^>]*>\s*<w:rPr>\s*<w:color[^/]*/>\s*<w:szCs[^/]*/>\s*</w:rPr>\s*'
            rf'<w:t xml:space="preserve"> Soft Notes\]</w:t>)'
        )
        
        def replacement(match):
            original = match.group(0)
            new_content = original
            new_content = re.sub(r'<w:t>\[</w:t>', '<w:t></w:t>', new_content)
            new_content = re.sub(
                rf'<w:t>{re.escape(xml_section_name)}</w:t>',
                f'<w:t>{escaped_value}</w:t>',
                new_content
            )
            new_content = re.sub(
                r'<w:t xml:space="preserve"> Soft Notes\]</w:t>',
                '<w:t xml:space="preserve"></w:t>',
                new_content
            )
            return new_content
        
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        return content
    
    def fill_template(self, template_dir: str, output_dir: str, data: dict, mapping_config: dict):
        """Fill the template with data using the mapping configuration."""
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        shutil.copytree(template_dir, output_dir)
        
        doc_path = os.path.join(output_dir, 'word', 'document.xml')
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        sections_config = mapping_config.get("sections", {})
        split_sections = mapping_config.get("split_placeholder_sections", [])
        bold_phrases_config = mapping_config.get("bold_phrases", {})
        
        today_date = datetime.now().strftime("%d-%B-%Y")
        if "Meeting" in data:
            data["Meeting"]["Document Generation Date"] = today_date
        
        # Process Meeting section
        meeting_config = sections_config.get("Meeting", {})
        meeting_json_key = meeting_config.get("json_key", "Meeting")
        
        for placeholder, field_name in meeting_config.get("placeholders", {}).items():
            value = self.get_value_from_json(data, meeting_json_key, field_name)
            
            if placeholder == "[Summary of Discussion]" and value != "Not Available":
                bold_phrases = bold_phrases_config.get("Summary of Discussion", [])
                formatted_value = format_as_newlines_with_bold(value, bold_phrases)
                content = self.replace_simple_placeholder(content, placeholder, formatted_value, is_hard_facts=True)
            elif placeholder == "[Actions & Recommendations]" and value != "Not Available":
                bold_phrases = bold_phrases_config.get("Actions & Recommendations", [])
                formatted_value = format_as_newlines_with_bold(value, bold_phrases)
                content = self.replace_simple_placeholder(content, placeholder, formatted_value, is_hard_facts=True)
            elif placeholder == "[Next Steps]" and value != "Not Available":
                formatted_value = format_as_newlines(value)
                content = self.replace_simple_placeholder(content, placeholder, formatted_value, is_hard_facts=True)
            else:
                content = self.replace_simple_placeholder(content, placeholder, value)
        
        print("  âœ“ Meeting section filled")
        
        # Process each data section
        for section_name, section_config in sections_config.items():
            if section_name == "Meeting":
                continue
            
            json_key = section_config.get("json_key", "")
            
            # ---------------------------------------------------------------------
            # GET SOFT NOTES
            # ---------------------------------------------------------------------
            soft_notes_field = section_config.get("soft_notes_field", "")
            soft_notes_placeholder = section_config.get("soft_notes_placeholder", "")

            # Check for combined soft notes (Income & Expenditure has 2 fields)
            soft_notes_field_2 = section_config.get("soft_notes_field_2", "")

            if soft_notes_field_2:
                soft_notes_raw = self.get_combined_soft_notes(data, json_key, soft_notes_field, soft_notes_field_2)
            else:
                soft_notes_raw = self.get_soft_notes(data, json_key, soft_notes_field)
            
            # Format soft notes
            if section_name == "Vulnerability" and soft_notes_raw != "No notes available.":
                soft_notes_value = format_vulnerability_soft_notes(soft_notes_raw)
            elif soft_notes_raw != "No notes available.":
                soft_notes_value = format_as_bullets(soft_notes_raw)
            else:
                soft_notes_value = soft_notes_raw
            
            # ---------------------------------------------------------------------
            # GET HARD FACTS (with dynamic array handling) - FIXED INDENTATION
            # ---------------------------------------------------------------------
            hard_facts_placeholder = section_config.get("hard_facts_placeholder", "")
            hard_facts_fields = section_config.get("hard_facts_fields", [])
            array_field = section_config.get("array_field", None)

            # Use dynamic array handler
            hard_facts_value = self.get_hard_facts_with_array(
                data, 
                json_key, 
                hard_facts_fields, 
                array_field
            )
            
            # ===== DEBUG 3: Check hard facts extraction =====
            print(f"\n[DEBUG 3] Section: {section_name}")
            print(f"[DEBUG 3] JSON key: {json_key}")
            print(f"[DEBUG 3] Hard facts placeholder: '{hard_facts_placeholder}'")
            print(f"[DEBUG 3] Hard facts fields: {hard_facts_fields}")
            print(f"[DEBUG 3] Hard facts value (first 200 chars): {str(hard_facts_value)[:200]}")
            print(f"[DEBUG 3] Placeholder in content: {hard_facts_placeholder in content}")
            
            # ---------------------------------------------------------------------
            # REPLACE PLACEHOLDERS
            # ---------------------------------------------------------------------
            original_content = content
            content = self.replace_simple_placeholder(content, soft_notes_placeholder, soft_notes_value, is_hard_facts=True)
            
            # If simple replacement didn't work, try split replacement
            if content == original_content and section_name in split_sections:
                content = self.replace_split_placeholder(content, section_name, soft_notes_value)
            
            # Replace hard facts placeholder
            original_content_hf = content  # Add this line
            content = self.replace_simple_placeholder(content, hard_facts_placeholder, hard_facts_value, is_hard_facts=True)
            print(f"[DEBUG 4] Hard facts replacement happened: {content != original_content_hf}")

            
            # Handle additional placeholders
            for placeholder, field_name in section_config.get("additional_placeholders", {}).items():
                value = self.get_value_from_json(data, json_key, field_name)
                content = self.replace_simple_placeholder(content, placeholder, value)
            
            print(f"  âœ“ {section_name} section filled")
        
        # =========================================================================
        # STEP 3: Clean up
        # =========================================================================
        content = content.replace('<w:t>[</w:t>', '<w:t></w:t>')
        content = content.replace("&amp;amp;", "&amp;")
        
        # Remove page break between cover page and Executive Summary
        content = re.sub(
            r'<w:br\s+w:type="page"\s*/>((?:(?!<w:br\s+w:type="page").){0,500}?Executive Summary)',
            r'\1',
            content,
            flags=re.DOTALL
        )
        
        # =========================================================================
        # STEP 4: Write back
        # =========================================================================
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("  âœ“ Template filled successfully")
    
    def run_generation(self, json_path: str, output_dir: str) -> Optional[str]:
        """Generate PDF from JSON data using template."""
        print("\n" + "=" * 60)
        print("STEP 2: PDF GENERATION")
        print("=" * 60)
        
            # DEBUG: Print template path
        print(f"DEBUG: Template path = {settings.TEMPLATE_PATH}")
        print(f"DEBUG: Template exists = {os.path.exists(settings.TEMPLATE_PATH)}")
            
        pdf_output_name = "final_output.pdf"
        pdf_output_path = os.path.join(output_dir, pdf_output_name)
        
        # Validate input files
        print("\n[2.1] Validating input files...")
        for name, path in [("JSON", json_path), ("Template", settings.TEMPLATE_PATH)]:
            if not os.path.exists(path):
                print(f"  âœ— ERROR: {name} file not found: {path}")
                return None
            print(f"  âœ“ {name}: {path}")
        
        # Create temp directories
        work_dir = tempfile.mkdtemp(prefix="ehon_fill_")
        template_unpacked = os.path.join(work_dir, "template_unpacked")
        filled_unpacked = os.path.join(work_dir, "filled_unpacked")
        
        try:
            # Load JSON data
            print("\n[2.2] Loading JSON data...")
            data = self.load_json_file(json_path)
            print(f"  âœ“ Loaded {len(data)} sections")
            
            # Unpack template
            print("\n[2.3] Unpacking template...")
            if not self.unpack_docx(settings.TEMPLATE_PATH, template_unpacked):
                print("  âœ— Failed to unpack template")
                return None
            print("  âœ“ Template unpacked")
            
            # Fill template
            print("\n[2.4] Filling template with data...")
            self.fill_template(template_unpacked, filled_unpacked, data, TEMPLATE_MAPPING)
            self.fix_fonts(filled_unpacked)
            print("  âœ“ Template filled")
            
            # Pack output (temporary docx)
            print("\n[2.5] Creating intermediate document...")
            temp_docx = os.path.join(work_dir, "temp_output.docx")
            if not self.pack_docx(filled_unpacked, temp_docx):
                print("  âœ— Failed to pack document")
                return None
            print("  âœ“ Intermediate document created")
            
            # Convert to PDF
            print("\n[2.6] Converting to PDF...")
            if not self.convert_docx_to_pdf(temp_docx, pdf_output_path):
                print("  âœ— Failed to convert to PDF")
                return None
            print(f"  âœ“ PDF saved: {pdf_output_path}")
            
            print("\n" + "-" * 60)
            print("PDF GENERATION COMPLETE")
            print("-" * 60)
            
            return pdf_output_path
            
        except Exception as e:
            print(f"\n  âœ— ERROR during PDF generation: {str(e)}")
            return None
            
        finally:
            if os.path.exists(work_dir):
                shutil.rmtree(work_dir)


# Global instance
pdf_service = PDFService()