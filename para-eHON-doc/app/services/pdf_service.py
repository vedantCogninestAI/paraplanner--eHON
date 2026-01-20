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
    
    def fix_fonts(self, unpacked_dir: str, font_name: str = "Arial"):
        """Replace all fonts with a universal font and fix text alignment."""
        
        def process_xml_file(file_path: str):
            if not os.path.exists(file_path):
                return False
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            content = re.sub(
                r'<w:rFonts[^>]*/>', 
                f'<w:rFonts w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="{font_name}" w:eastAsia="{font_name}"/>', 
                content
            )
            
            content = re.sub(
                r'<w:rFonts[^>]*>.*?</w:rFonts>', 
                f'<w:rFonts w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="{font_name}" w:eastAsia="{font_name}"/>', 
                content,
                flags=re.DOTALL
            )
            
            content = re.sub(r'\s*w:asciiTheme="[^"]*"', '', content)
            content = re.sub(r'\s*w:hAnsiTheme="[^"]*"', '', content)
            content = re.sub(r'\s*w:cstheme="[^"]*"', '', content)
            content = re.sub(r'\s*w:eastAsiaTheme="[^"]*"', '', content)
            
            content = re.sub(r'<w:jc\s+w:val\s*=\s*"both"\s*/>', '<w:jc w:val="left"/>', content)
            content = re.sub(r'<w:jc\s+w:val\s*=\s*"both"\s*>', '<w:jc w:val="left">', content)
            
            def replace_both_in_jc(match):
                return match.group(0).replace('"both"', '"left"').replace("'both'", "'left'")
            
            content = re.sub(r'<w:jc[^>]*>', replace_both_in_jc, content)
            
            def fix_pPr_justification(match):
                pPr_content = match.group(0)
                pPr_content = re.sub(r'"both"', '"left"', pPr_content)
                pPr_content = re.sub(r"'both'", "'left'", pPr_content)
                return pPr_content
            
            content = re.sub(r'<w:pPr>.*?</w:pPr>', fix_pPr_justification, content, flags=re.DOTALL)
            content = re.sub(r'<w:pPrDefault>.*?</w:pPrDefault>', fix_pPr_justification, content, flags=re.DOTALL)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        doc_path = os.path.join(unpacked_dir, 'word', 'document.xml')
        process_xml_file(doc_path)
        
        styles_path = os.path.join(unpacked_dir, 'word', 'styles.xml')
        process_xml_file(styles_path)
        
        numbering_path = os.path.join(unpacked_dir, 'word', 'numbering.xml')
        process_xml_file(numbering_path)
        
        settings_path = os.path.join(unpacked_dir, 'word', 'settings.xml')
        process_xml_file(settings_path)
        
        word_dir = os.path.join(unpacked_dir, 'word')
        if os.path.exists(word_dir):
            for filename in os.listdir(word_dir):
                if filename.startswith('header') and filename.endswith('.xml'):
                    process_xml_file(os.path.join(word_dir, filename))
                if filename.startswith('footer') and filename.endswith('.xml'):
                    process_xml_file(os.path.join(word_dir, filename))
        
        print(f"  ✓ Fonts standardized to {font_name}")
    
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
        
        print("  ✓ Meeting section filled")
        
        # Process each data section
        for section_name, section_config in sections_config.items():
            if section_name == "Meeting":
                continue
            
            json_key = section_config.get("json_key", "")
            
            soft_notes_field = section_config.get("soft_notes_field", "")
            soft_notes_placeholder = section_config.get("soft_notes_placeholder", "")
            soft_notes_raw = self.get_soft_notes(data, json_key, soft_notes_field)
            
            if section_name == "Vulnerability" and soft_notes_raw != "No notes available.":
                soft_notes_value = format_vulnerability_soft_notes(soft_notes_raw)
            elif soft_notes_raw != "No notes available.":
                soft_notes_value = format_as_bullets(soft_notes_raw)
            else:
                soft_notes_value = soft_notes_raw
            
            hard_facts_placeholder = section_config.get("hard_facts_placeholder", "")
            hard_facts_fields = section_config.get("hard_facts_fields", [])
            hard_facts_value = self.get_hard_facts_formatted(data, json_key, hard_facts_fields)
            
            original_content = content
            content = self.replace_simple_placeholder(content, soft_notes_placeholder, soft_notes_value, is_hard_facts=True)
            
            if content == original_content and section_name in split_sections:
                content = self.replace_split_placeholder(content, section_name, soft_notes_value)
            
            content = self.replace_simple_placeholder(content, hard_facts_placeholder, hard_facts_value, is_hard_facts=True)
            
            for placeholder, field_name in section_config.get("additional_placeholders", {}).items():
                value = self.get_value_from_json(data, json_key, field_name)
                content = self.replace_simple_placeholder(content, placeholder, value)
            
            print(f"  ✓ {section_name} section filled")
        
        content = content.replace('<w:t>[</w:t>', '<w:t></w:t>')
        content = content.replace("&amp;amp;", "&amp;")
        
        # Remove page break between cover page and Executive Summary
        content = re.sub(
            r'<w:br\s+w:type="page"\s*/>((?:(?!<w:br\s+w:type="page").){0,500}?Executive Summary)',
            r'\1',
            content,
            flags=re.DOTALL
        )
        
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("  ✓ Template filled successfully")
    
    def run_generation(self, json_path: str, output_dir: str) -> Optional[str]:
        """Generate PDF from JSON data using template."""
        print("\n" + "=" * 60)
        print("STEP 2: PDF GENERATION")
        print("=" * 60)
        
        pdf_output_name = "final_output.pdf"
        pdf_output_path = os.path.join(output_dir, pdf_output_name)
        
        # Validate input files
        print("\n[2.1] Validating input files...")
        for name, path in [("JSON", json_path), ("Template", settings.TEMPLATE_PATH)]:
            if not os.path.exists(path):
                print(f"  ✗ ERROR: {name} file not found: {path}")
                return None
            print(f"  ✓ {name}: {path}")
        
        # Create temp directories
        work_dir = tempfile.mkdtemp(prefix="ehon_fill_")
        template_unpacked = os.path.join(work_dir, "template_unpacked")
        filled_unpacked = os.path.join(work_dir, "filled_unpacked")
        
        try:
            # Load JSON data
            print("\n[2.2] Loading JSON data...")
            data = self.load_json_file(json_path)
            print(f"  ✓ Loaded {len(data)} sections")
            
            # Unpack template
            print("\n[2.3] Unpacking template...")
            if not self.unpack_docx(settings.TEMPLATE_PATH, template_unpacked):
                print("  ✗ Failed to unpack template")
                return None
            print("  ✓ Template unpacked")
            
            # Fill template
            print("\n[2.4] Filling template with data...")
            self.fill_template(template_unpacked, filled_unpacked, data, TEMPLATE_MAPPING)
            self.fix_fonts(filled_unpacked)
            print("  ✓ Template filled")
            
            # Pack output (temporary docx)
            print("\n[2.5] Creating intermediate document...")
            temp_docx = os.path.join(work_dir, "temp_output.docx")
            if not self.pack_docx(filled_unpacked, temp_docx):
                print("  ✗ Failed to pack document")
                return None
            print("  ✓ Intermediate document created")
            
            # Convert to PDF
            print("\n[2.6] Converting to PDF...")
            if not self.convert_docx_to_pdf(temp_docx, pdf_output_path):
                print("  ✗ Failed to convert to PDF")
                return None
            print(f"  ✓ PDF saved: {pdf_output_path}")
            
            print("\n" + "-" * 60)
            print("PDF GENERATION COMPLETE")
            print("-" * 60)
            
            return pdf_output_path
            
        except Exception as e:
            print(f"\n  ✗ ERROR during PDF generation: {str(e)}")
            return None
            
        finally:
            if os.path.exists(work_dir):
                shutil.rmtree(work_dir)


# Global instance
pdf_service = PDFService()