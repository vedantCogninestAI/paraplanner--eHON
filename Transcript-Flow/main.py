"""
Paraplanner FastAPI Application
===============================
Two endpoints:
1. POST /process - Process transcript/audio and generate PDF
2. GET /download/{filename} - Download the generated PDF
"""
import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import json
import time
import shutil
import tempfile
import re
import zipfile
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


import pandas as pd
from docx import Document
import assemblyai as aai

# Try to import docx2pdf, but handle if not available (Linux)
try:
    from docx2pdf import convert as docx2pdf_convert
    DOCX2PDF_AVAILABLE = True
except ImportError:
    DOCX2PDF_AVAILABLE = False

# =============================================================================
# CONFIGURATION
# =============================================================================



# LLM Configuration
CHAT_DAILOQA_LLM_MODEL = os.getenv("MODEL_NAME")           # ✅ Matches .env
LITELLM_BASE_URL = os.getenv("DAILOQA_LLM_BASE_URL")       # ✅ Matches .env
LITELLM_API_KEY = os.getenv("DAILOQA_LLM_API_KEY")         # ✅ Matches .env
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")       # ✅ Matches .env

# File paths - these should be configured based on your deployment
EXCEL_PATH = os.getenv("EXCEL_PATH", "./files/Paraplanner_Extraction and Rules_v2.xlsx")
SHEET_NAME = os.getenv("SHEET_NAME", "Extraction Fields_JSON")
TEMPLATE_PATH = os.getenv("TEMPLATE_PATH", "./files/latest_but_modifie.docx")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./outputs")

# Initialize AssemblyAI
if ASSEMBLYAI_API_KEY:
    aai.settings.api_key = ASSEMBLYAI_API_KEY

# =============================================================================
# INITIALIZE CHAT CLIENT
# =============================================================================

from dailoqa_sdk.chat_ai import ChatDailoqa

chat = ChatDailoqa(
    base_url=LITELLM_BASE_URL,
    api_key=LITELLM_API_KEY,
    model=CHAT_DAILOQA_LLM_MODEL
)

# =============================================================================
# FASTAPI APP
# =============================================================================

app = FastAPI(
    title="Paraplanner API",
    description="API for processing financial transcripts and generating PDF reports",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store for tracking processed files
processed_files: Dict[str, dict] = {}

# =============================================================================
# TEMPLATE MAPPING CONFIG
# =============================================================================

TEMPLATE_MAPPING = {
    "version": "1.0",
    "description": "Template placeholder to JSON path mapping for eHON template",
    
    "bold_phrases": {
        "Summary of Discussion": [
            "Vulnerability",
            "Personal Details",
            "Other Business",
            "Retirement Planning",
            "Income & Expenditure",
            "Loans & Liabilities",
            "Savings & Investments",
            "Taxation & Estate Planning",
            "Attitude to Risk",
            "Additional Products",
            "Goals & Objectives"
        ],
        "Actions & Recommendations": [
            "Immediate",
            "Medium-Term",
            "Long-Term"
        ],
        "Next Steps": []
    },

    "sections": {
        "Meeting": {
            "json_key": "Meeting",
            "placeholders": {
                "[Meeting Objective]": "Meeting Objective",
                "[Adviser Name]": "Adviser Name",
                "[Meeting Date]": "Meeting Date",
                "[Meeting Format]": "Meeting Format",
                "[Opportunity Value]": "Opportunity Value",
                "[Document Generation Date]": "Document Generation Date",
                "[Executive Summary]": "Executive Summary",
                "[Summary of Discussion]": "Summary of Discussion",
                "[Actions & Recommendations]": "Actions & Recommendations",
                "[Next Steps]": "Next Steps"
            }
        },

        "Personal Details": {
            "json_key": "1. Personal Details",
            "soft_notes_placeholder": "[Personal Details Soft Notes]",
            "soft_notes_field": "Personal Details Soft Notes",
            "hard_facts_placeholder": "[Personal Details]",
            "hard_facts_fields": [
                "Client Name(s)",
                "Age",
                "Marital Status",
                "Country of Residence",
                "UK Resident for Tax",
                "UK Domicile",
                "Accommodation Type",
                "Employment Status",
                "Director",
                "Family Details"
            ],
            "additional_placeholders": {
                "[Client Name(s)]": "Client Name(s)"
            },
            "is_split_placeholder": False
        },

        "Vulnerability": {
            "json_key": "2. Vulnerability",
            "soft_notes_placeholder": "[Vulnerability Soft Notes]",
            "soft_notes_field": "Vulnerability Soft Notes",
            "hard_facts_placeholder": "[Vulnerability]",
            "hard_facts_fields": [
                "Long-term Vulnerabilities",
                "Circumstantial Vulnerabilities"
            ]
        },

        "Other Business": {
            "json_key": "3. Other Business",
            "soft_notes_placeholder": "[Other Business Soft Notes]",
            "soft_notes_field": "Other Business Soft Notes",
            "hard_facts_placeholder": "[Other Business]",
            "hard_facts_fields": [],
            "is_split_placeholder": False
        },

        "Retirement Planning": {
            "json_key": "4. Retirement Planning",
            "soft_notes_placeholder": "[Retirement Planning Soft Notes]",
            "soft_notes_field": "Retirement Planning Soft Notes",
            "hard_facts_placeholder": "[Retirement Planning]",
            "hard_facts_fields": [
                "Intended Retirement Age",
                "Income Required in Retirement"
            ],
            "is_split_placeholder": False
        },

        "Income & Expenditure": {
            "json_key": "5. Income & Expenditure",
            "soft_notes_placeholder": "[Income & Expenditure Soft Notes]",
            "soft_notes_field": "Income & Expenditure Soft Notes",
            "hard_facts_placeholder": "[Income & Expenditure]",
            "hard_facts_fields": [
                "Total Net Monthly Income",
                "Monthly Surplus Income",
                "Total Monthly Expenditure"
            ],
            "is_split_placeholder": False
        },

        "Loans & Liabilities": {
            "json_key": "6. Loans & Liabilities",
            "soft_notes_placeholder": "[Loans & Liabilities Soft Notes]",
            "soft_notes_field": "Loans & Liabilities Soft Notes",
            "hard_facts_placeholder": "[Loans & Liabilities]",
            "hard_facts_fields": [
                "Loans"
            ],
            "is_split_placeholder": False
        },

        "Savings & Investments": {
            "json_key": "7. Savings & Investments",
            "soft_notes_placeholder": "[Savings & Investments Soft Notes]",
            "soft_notes_field": "Savings & Investments Soft Notes",
            "hard_facts_placeholder": "[Savings & Investments]",
            "hard_facts_fields": [
                "Total Assets",
                "Home",
                "Cash",
                "Pension Funds"
            ],
            "is_split_placeholder": False
        },

        "Taxation": {
            "json_key": "8. Taxation",
            "soft_notes_placeholder": "[Taxation Soft Notes]",
            "soft_notes_field": "Taxation Soft Notes",
            "hard_facts_placeholder": "[Taxation]",
            "hard_facts_fields": [
                "Taxation on Withdrawal (Chargeable Gains, CGT, IHT Liability)",
                "Tax Planning Strategies",
                "Client Tax Preferences"
            ],
            "is_split_placeholder": False
        },

        "Protection": {
            "json_key": "9. Protection",
            "soft_notes_placeholder": "[Protection Soft Notes]",
            "soft_notes_field": "Protection Soft Notes",
            "hard_facts_placeholder": "[Protection]",
            "hard_facts_fields": [
                "Product Type"
            ],
            "is_split_placeholder": False
        },

        "Additional Products": {
            "json_key": "10. Additional Products",
            "soft_notes_placeholder": "[Additional Products Soft Notes]",
            "soft_notes_field": "Additional Products Soft Notes",
            "hard_facts_placeholder": "[Additional Products]",
            "hard_facts_fields": [
                "Product Type",
                "Provider Name"
            ],
            "is_split_placeholder": False
        },

        "Estate Planning": {
            "json_key": "11. Estate Planning",
            "soft_notes_placeholder": "[Estate Planning Soft Notes]",
            "soft_notes_field": "Estate Planning Soft Notes",
            "hard_facts_placeholder": "[Estate Planning]",
            "hard_facts_fields": [
                "Estate Value",
                "Inheritance Tax Liability",
                "Gifting Strategy",
                "Trusts & ISAs"
            ],
            "is_split_placeholder": False
        },

        "Attitude to Risk": {
            "json_key": "12. Attitude to Risk",
            "soft_notes_placeholder": "[Attitude to Risk Soft Notes]",
            "soft_notes_field": "Attitude to Risk Soft Notes",
            "hard_facts_placeholder": "[Attitude to Risk]",
            "hard_facts_fields": [
                "Capacity for Loss"
            ],
            "is_split_placeholder": False
        },

        "Goals & Objectives": {
            "json_key": "13. Goals & Objectives",
            "soft_notes_placeholder": "[Goals & Objectives Soft Notes]",
            "soft_notes_field": "Goals & Objectives Soft Notes",
            "hard_facts_placeholder": "[Goals & Objectives]",
            "hard_facts_fields": [
                "Client Objectives",
                "Investment Objectives Summary",
                "Goal Owner (Goal is for)",
                "Goal Description",
                "Client wants to",
                "Goal Name",
                "Status"
            ],
            "is_split_placeholder": False
        }
    },

    "split_placeholder_sections": [
        "Other Business",
        "Retirement Planning",
        "Income & Expenditure",
        "Loans & Liabilities",
        "Savings & Investments",
        "Estate Planning",
        "Attitude to Risk",
        "Goals & Objectives"
    ]
}

# =============================================================================
# TRANSCRIPT FUNCTIONS
# =============================================================================

def transcribe_with_diarization(audio_path: str) -> tuple:
    """Transcribe audio with speaker diarization using AssemblyAI"""
    print("Transcribing audio with speaker diarization...")
    
    config = aai.TranscriptionConfig(speaker_labels=True)
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_path, config=config)
    
    if transcript.status == aai.TranscriptStatus.error:
        print(f"Transcription failed: {transcript.error}")
        return None, None
    
    formatted_transcript = ""
    plain_transcript = ""
    
    for utterance in transcript.utterances:
        formatted_transcript += f"Speaker {utterance.speaker}: {utterance.text}\n"
        plain_transcript += f"{utterance.text} "
    
    return formatted_transcript, plain_transcript.strip()


def read_docx_transcript(docx_path: str) -> str:
    """Read transcript from a DOCX file"""
    doc = Document(docx_path)
    transcript_text = []
    for para in doc.paragraphs:
        if para.text.strip():
            transcript_text.append(para.text)
    return '\n'.join(transcript_text)


def read_vtt_transcript(vtt_path: str) -> str:
    """Read transcript from a VTT (WebVTT) file"""
    with open(vtt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = re.sub(r'^WEBVTT.*?\n\n', '', content, flags=re.MULTILINE)
    blocks = content.split('\n\n')
    transcript_lines = []
    
    for block in blocks:
        lines = block.strip().split('\n')
        if not lines or not lines[0].strip():
            continue
        text_lines = [line for line in lines if '-->' not in line]
        for line in text_lines:
            line = line.strip()
            if line and not line.isdigit():
                line = re.sub(r'<v\s+([^>]+)>', r'\1: ', line)
                line = re.sub(r'</?[^>]+>', '', line)
                transcript_lines.append(line)
    
    return '\n'.join(transcript_lines)


def read_txt_transcript(txt_path: str) -> str:
    """Read transcript from a plain text file"""
    with open(txt_path, 'r', encoding='utf-8') as f:
        return f.read()


def read_transcript(file_path: str) -> str:
    """Read transcript based on file extension"""
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension == '.docx':
        print(f"Reading DOCX file: {file_path}")
        return read_docx_transcript(file_path)
    elif file_extension == '.vtt':
        print(f"Reading VTT file: {file_path}")
        return read_vtt_transcript(file_path)
    elif file_extension == '.txt':
        print(f"Reading TXT file: {file_path}")
        return read_txt_transcript(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_extension}. Supported: .docx, .vtt, .txt")


# =============================================================================
# EXTRACTION FUNCTIONS
# =============================================================================

def load_field_definitions_from_excel(excel_path: str, sheet_name: str) -> Dict[str, Dict[str, str]]:
    """Load field definitions from Excel"""
    print(f"Loading field definitions from {excel_path}...")
    
    df = pd.read_excel(excel_path, sheet_name=sheet_name)
    df = df[df['Field'].notna()]
    
    field_schema = {}
    
    for _, row in df.iterrows():
        field_name = str(row['Field']).strip()
        description = str(row['Description']).strip() if pd.notna(row.get('Description')) else ''
        section = str(row['Section / Data Category']).strip() if pd.notna(row.get('Section / Data Category')) else ''
        
        if section not in field_schema:
            field_schema[section] = {}
        
        field_schema[section][field_name] = {
            'description': description
        }
    
    print(f"✓ Loaded {len(field_schema)} sections with field definitions")
    return field_schema


def create_json_schema(field_schema: Dict[str, Dict[str, str]]) -> str:
    """Create JSON schema string from field schema"""
    schema_lines = []
    for section, fields in field_schema.items():
        for field_name, metadata in fields.items():
            description = metadata['description']
            schema_line = f'  "{section}" -> "{field_name}" : {description}'
            schema_lines.append(schema_line)
    return '\n'.join(schema_lines)


def extract_all_fields(transcript: str, field_schema: Dict[str, Dict[str, str]]) -> str:
    """Extract ALL fields in a SINGLE API call"""
    print(f"Extracting ALL {len(field_schema)} sections in a SINGLE API call...")
    
    current_date = datetime.now().strftime("%d-%B-%Y")
    schema_string = create_json_schema(field_schema)
    total_fields = sum(len(fields) for fields in field_schema.values())
    print(f"  Total fields to extract: {total_fields}")
    
    prompt = f"""
You are a financial data extraction assistant SPECIFICALLY FOR THE CLIENT (NOT THE ADVISER). Analyze the following conversation transcript between a financial advisor and client.

TRANSCRIPT:
{transcript}
==============================================
FIELD SCHEMA WITH BUSINESS RULES:
{schema_string}

==============================================
INSTRUCTIONS:

Each field has a business rule description that contains complete instructions for that field.

Your task: Read each business rule carefully and follow it exactly as written. The business rule describes:
- Whether to use a fixed/static value or extract from transcript
- What to do if information is not available

==============================================

=== CRITICAL: CLIENT vs ADVISER DISTINCTION ===

Before extracting, identify:
- CLIENT: The person receiving financial advice. For fields where the description mentions family, spouse, or household, include relevant family members' information as well.
- ADVISER: The professional giving advice (DO NOT extract their personal info into client fields)

For each piece of information ask: "Is this relevant to the CLIENT's financial planning?"
- If about the ADVISER's personal health, family, personal life → EXCLUDE
- If about the ADVISORY FIRM's internal operations (IT issues, staff matters) → EXCLUDE
- If about the CLIENT or their household → INCLUDE
- If adviser statement directly affects client's options (e.g., service limitations) → INCLUDE
- If adviser explains financial concepts/rules to client → INCLUDE

==============================================

=== COMPREHENSIVE EXTRACTION FOR SOFT NOTES ===

SOFT NOTES ARE THE MOST IMPORTANT FIELDS. They must be EXHAUSTIVE and capture EVERYTHING relevant. Follow these rules:

1. **QUANTITATIVE DETAILS (MANDATORY)**: Extract ALL specific numbers mentioned:
   - Percentages (e.g., "4.6% return")
   - Monetary amounts (e.g.,  "£4,000/year")
   - Time periods (e.g., "2-year rule")
   - Rates and returns (e.g., "1.78% from techo")

2. **PLATFORMS & PROVIDERS (MANDATORY)**: Capture ALL financial platforms, providers, and products mentioned by name (e.g., Saltus, Investec, Raisin, TPT).

3. **HOUSEHOLD MEMBERS (MANDATORY)**: Include relevant details for ALL family members:
   - Spouse: employment status, pension details, retirement plans, income
   - Children: location, employment, financial needs (e.g., house deposits), transition plans
   - Grandchildren: education plans, Junior ISAs, inheritance considerations

4. **PLANNING CONCEPTS EXPLAINED (MANDATORY)**: When the adviser explains a financial concept, rule, or strategy to the client, capture the explanation INCLUDING specific rules:
   - Tax rules 
   - Trust mechanics 
   - Product features 
   
5. **CONSTRAINTS & LIMITATIONS (MANDATORY)**: Capture any constraints mentioned:
   - Service limitations 
   - Regulatory constraints
   - Client-specific constraints

6. **FUTURE PLANS & INTENTIONS (MANDATORY)**: Capture ALL stated future plans:
   - Retirement timeline for all household members
   - Moving/relocation plans
   - Career changes
   - Education plans for children/grandchildren

**WHAT TO EXCLUDE:**

- Small talk and social conversation
- Personal anecdotes unrelated to finances (e.g., holiday stories, health scares unless affecting financial decisions)
- Filler phrases and conversational padding
- Repetitive information (state once, not multiple times)
- Adviser's personal life or firm's internal matters

EXAMPLE - What to exclude: "They caught COVID during their birthday trip to Glasgow" - NOT relevant unless it directly impacts financial planning.
EXAMPLE - What to include: "The client plans to retire next year when their professional revalidation expires" - RELEVANT to retirement planning.

**CROSS-REFERENCE CHECK**: Before finalizing any Soft Notes field, scan the ENTIRE transcript for:
- Any numerical values you might have missed
- Any family member details not yet captured
- Any adviser explanations of rules/concepts
- Any future plans or intentions mentioned


CRITICAL FORMATTING RULES FOR SOFT NOTES 

**SENTENCE STRUCTURE**:
- Write complete, standalone sentences
- Each sentence should convey one clear piece of information
- Avoid run-on sentences with multiple data points
- Start each new fact on a logical sentence boundary

==============================================

=== FIELD-SPECIFIC GUIDANCE ===

For each Soft Notes field, ensure you capture information that matches the field's schema description. Cross-reference with related fields to ensure completeness:

- **Client Name field** : Specifically for the client name field, extract the FULL name of the PRIMARY client ONLY. Do NOT include adviser or family member names.

- **Personal Details Soft Notes**: Include employment details, lifestyle, family support plans, AND any household members' employment/retirement plans.

- **Other Business Soft Notes**: Include non-financial business activities AND any discussions about family members' financial transitions (e.g., moving assets between countries).

- **Retirement Planning Soft Notes**: Include ALL pension pot values mentioned (for client AND spouse), income drawdown strategies, AND specific concerns about sustainability.

- **Savings & Investments Soft Notes**: Include ALL performance metrics (percentages, returns), ALL platforms mentioned, ALL interest rates, AND portfolio composition details.

- **Protection Soft Notes**: Include product types, coverage amounts, AND premium details (monthly AND annual amounts).

- **Estate Planning Soft Notes**: Include ALL tax rules explained (e.g., 7-year rule), ALL strategies discussed, AND specific products for grandchildren (e.g., Junior ISAs, pensions).

- **Goals & Objectives Soft Notes**: Include goals for the PRIMARY client AND goals related to supporting family members (e.g., helping with house deposits, funding grandchildren's education).

==============================================

=== OUTPUT FORMAT ===

For **every field**, produce in this format with (3-4 lines of evidence):
```
[Field #X.Y] 
Section_name: **EXACT Name of the section as per schema**
field_name : **EXACT Name of the field**
Evidence: "SHORT REASONING [exact quote 1]" (Page X), "[exact quote 2]" (Page Y), ... OR "Not found"  
Value: [extracted value - be COMPREHENSIVE for Soft Notes] | Reason: [clear explanation]
```

For Soft Notes fields specifically:
- The "Value" should be a COMPREHENSIVE narrative
- Include ALL relevant quotes as Evidence, not just one
- Do NOT summarize - capture ALL details

==============================================

Key principles:
1. If the business rule provides a specific value or text, use that value
2. If the business rule asks you to extract from transcript, search THOROUGHLY
3. Follow any conditional logic in the rule
4. Extract ALL fields from the schema
5. Do NOT add any fields not in the schema
6. For "Soft Notes" fields: Be EXHAUSTIVE. Include specific figures, amounts, percentages, names, rules explained, and contextual details. Soft Notes are meant to be comprehensive. When in doubt, INCLUDE the information.
7. For other fields: Be detailed and accurate. Do not assume things.
8. Do not calculate any value on your own, Only extract the values that is specifically mentioned.
9. For ALL 'Soft Notes' fields specifically: Write in plain continuous prose sentences. Do NOT use numbered lists, bullet points, markdown formatting (**, *), or HTML tags. Just flowing narrative paragraphs.
10. MULTIPLE PASSES: After completing initial extraction, do a second pass specifically looking for:
   - Numerical values (percentages, amounts, rates)
   - Family member details
   - Adviser explanations of rules/concepts
   - Premium/cost information

Think step by step for each field, extract the data as per the instructions and field description.

WARNING : DO NOT ASSUME OR ADD INFORMATION THAT IS NOT THERE IN THE TRANSCRIPT. THE EXTRACTION SHOULD STICK WITHING THE TRACRIPT DATA ONLY

START THE EXTRACTION NOW as per the strict **OUTPUT FORMAT**
"""
    
    print("  Sending request to Gemini API...")
    response = chat.invoke(prompt)
    response_text = response.content
    return response_text


def generate_json(extracted_json: str) -> str:
    """Convert extracted data to JSON format"""
    prompt = f"""
Convert the extracted data to JSON format.

EXTRACTED DATA:
==============================================
{extracted_json}
==============================================

STRICT RULES:
1. Use EXACT section and field names from the extracted data
2. Output valid JSON only (double quotes, no markdown blocks)
3. Include ALL sections: "Meeting" AND numbered sections "1. Personal Details" through "13. Goals & Objectives"

OUTPUT FORMAT:
{{
  "Meeting": {{
    "Meeting Objective": "<value>",
    "Adviser Name": "<value>",
    "Meeting Date": "<value>",
    "Meeting Format": "<value>",
    "Opportunity Value": "<value>",
    "Document Generation Date": "<value>",
    "Executive Summary": "<value>",
    "Summary of Discussion": "<value>",
    "Actions & Recommendations": "<value>",
    "Next Steps": "<value>"
  }},
  "1. Personal Details": {{
    "<field>": "<value>",
    "Personal Details Soft Notes": "<value>"
  }},
  "2. Vulnerability": {{ ... }},
  ... continue for all sections through "13. Goals & Objectives"
}}
"""

    print("Sending request to Gemini API...")
    response = chat.invoke(prompt)
    response_text = response.content

    if response_text:
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        elif response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

    return response_text


# =============================================================================
# PDF GENERATION FUNCTIONS
# =============================================================================

def load_json_file(file_path: str) -> dict:
    """Load a JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def convert_docx_to_pdf(docx_path: str, output_pdf_path: str) -> bool:
    """Convert a DOCX file to PDF."""
    if DOCX2PDF_AVAILABLE:
        try:
            docx2pdf_convert(docx_path, output_pdf_path)
            print(f"  Converted to PDF: {output_pdf_path}")
            return True
        except Exception as e:
            print(f"  Error converting to PDF: {e}")
            return False
    else:
        # On Linux, try using LibreOffice
        try:
            import subprocess
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


def fix_fonts(unpacked_dir: str, font_name: str = "Arial"):
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


def smart_sentence_split(text: str) -> list:
    """Split text into sentences without breaking on decimal numbers."""
    if not text:
        return []
    
    protected = text
    protected = re.sub(r'(\d+)\.(\d+)', r'\1<DEC>\2', protected)
    
    for abbr in ['e.g.', 'i.e.', 'vs.', 'etc.']:
        protected = protected.replace(abbr, abbr.replace('.', '<DEC>'))
    
    sentences = re.split(r'\.\s+(?=[A-Z])', protected)
    
    result = []
    for s in sentences:
        s = s.replace('<DEC>', '.').strip()
        if s:
            if not s.endswith('.'):
                s += '.'
            result.append(s)
    
    return result


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


def get_value_from_json(data: dict, section_key: str, field_name: str) -> str:
    """Get a value from the JSON data using section key and field name."""
    section_data = data.get(section_key, {})
    if not section_data:
        return "Not Available"
    
    value = section_data.get(field_name, "Not Available")
    return value if value else "Not Available"


def get_soft_notes(data: dict, section_key: str, soft_notes_field: str) -> str:
    """Get soft notes for a section."""
    value = get_value_from_json(data, section_key, soft_notes_field)
    
    empty_values = ["not available", "not found", "na", "n a", "none", "null", ""]
    
    if not value:
        return "No notes available."
    
    normalized = re.sub(r'[^a-z0-9\s]', '', str(value).lower()).strip()
    
    if normalized in empty_values:
        return "No notes available."
    
    return value


def format_as_bullets(text: str, font_name: str = "Arial") -> str:
    """Format soft notes text as bullet points."""
    if not text or text == "No notes available.":
        return text
    
    sentences = smart_sentence_split(text)
    if not sentences:
        return escape_xml(text)
    
    bullet_char = "•"
    
    result = (
        f'</w:t></w:r>'
        f'<w:r><w:rPr><w:rFonts w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="{font_name}"/></w:rPr>'
        f'<w:t>{bullet_char} {escape_xml(sentences[0])}'
    )
    
    for sentence in sentences[1:]:
        result += (
            f'</w:t></w:r>'
            f'<w:r><w:rPr><w:rFonts w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="{font_name}"/></w:rPr>'
            f'<w:br/><w:t>{bullet_char} {escape_xml(sentence)}'
        )
    
    result += '</w:t></w:r><w:r><w:t>'
    
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
                sentences = smart_sentence_split(content)
                
                for sentence in sentences:
                    if not sentence:
                        continue
                    
                    bullet_xml = (
                        f'<w:r><w:rPr><w:rFonts w:ascii="{font_name}" w:hAnsi="{font_name}" w:cs="{font_name}"/></w:rPr>'
                        f'<w:br/><w:t xml:space="preserve">{bullet_char} {escape_xml(sentence)}</w:t></w:r>'
                    )
                    result_parts.append(bullet_xml)
            
            i += 2
        else:
            i += 1
    
    if not result_parts:
        return format_as_bullets(text, font_name)
    
    final_result = ''.join(result_parts) + '<w:r><w:t>'
    
    return final_result


def get_hard_facts_formatted(data: dict, section_key: str, fields: list, font_name: str = "Arial") -> str:
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
    
    return "<w:r><w:br/></w:r>".join(facts)


def unpack_docx(docx_path: str, output_dir: str) -> bool:
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


def pack_docx(unpacked_dir: str, output_path: str) -> bool:
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


def replace_simple_placeholder(content: str, placeholder: str, value: str, is_hard_facts: bool = False, font_name: str = "Arial") -> str:
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


def replace_split_placeholder(content: str, section_name: str, soft_notes_value: str) -> str:
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


def fill_template(template_dir: str, output_dir: str, data: dict, mapping_config: dict):
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
        value = get_value_from_json(data, meeting_json_key, field_name)
        
        if placeholder == "[Summary of Discussion]" and value != "Not Available":
            bold_phrases = bold_phrases_config.get("Summary of Discussion", [])
            formatted_value = format_as_newlines_with_bold(value, bold_phrases)
            content = replace_simple_placeholder(content, placeholder, formatted_value, is_hard_facts=True)
        elif placeholder == "[Actions & Recommendations]" and value != "Not Available":
            bold_phrases = bold_phrases_config.get("Actions & Recommendations", [])
            formatted_value = format_as_newlines_with_bold(value, bold_phrases)
            content = replace_simple_placeholder(content, placeholder, formatted_value, is_hard_facts=True)
        elif placeholder == "[Next Steps]" and value != "Not Available":
            formatted_value = format_as_newlines(value)
            content = replace_simple_placeholder(content, placeholder, formatted_value, is_hard_facts=True)
        else:
            content = replace_simple_placeholder(content, placeholder, value)
    
    print("  ✓ Meeting section filled")
    
    # Process each data section
    for section_name, section_config in sections_config.items():
        if section_name == "Meeting":
            continue
        
        json_key = section_config.get("json_key", "")
        
        soft_notes_field = section_config.get("soft_notes_field", "")
        soft_notes_placeholder = section_config.get("soft_notes_placeholder", "")
        soft_notes_raw = get_soft_notes(data, json_key, soft_notes_field)
        
        if section_name == "Vulnerability" and soft_notes_raw != "No notes available.":
            soft_notes_value = format_vulnerability_soft_notes(soft_notes_raw)
        elif soft_notes_raw != "No notes available.":
            soft_notes_value = format_as_bullets(soft_notes_raw)
        else:
            soft_notes_value = soft_notes_raw
        
        hard_facts_placeholder = section_config.get("hard_facts_placeholder", "")
        hard_facts_fields = section_config.get("hard_facts_fields", [])
        hard_facts_value = get_hard_facts_formatted(data, json_key, hard_facts_fields)
        
        original_content = content
        content = replace_simple_placeholder(content, soft_notes_placeholder, soft_notes_value, is_hard_facts=True)
        
        if content == original_content and section_name in split_sections:
            content = replace_split_placeholder(content, section_name, soft_notes_value)
        
        content = replace_simple_placeholder(content, hard_facts_placeholder, hard_facts_value, is_hard_facts=True)
        
        for placeholder, field_name in section_config.get("additional_placeholders", {}).items():
            value = get_value_from_json(data, json_key, field_name)
            content = replace_simple_placeholder(content, placeholder, value)
        
        print(f"  ✓ {section_name} section filled")
    
    content = content.replace('<w:t>[</w:t>', '<w:t></w:t>')
    content = content.replace("&amp;amp;", "&amp;")
    
    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("  ✓ Template filled successfully")


# =============================================================================
# PIPELINE FUNCTIONS
# =============================================================================

def run_fpq_extraction(transcript_text: str, output_dir: str) -> Optional[str]:
    """Extract data from transcript and generate JSON output."""
    print("\n" + "=" * 60)
    print("STEP 1: FPQ EXTRACTION")
    print("=" * 60)
    
    json_output_name = "final_output.json"
    
    try:
        # Load field definitions
        print("\n[1.1] Loading field definitions from Excel...")
        field_schema = load_field_definitions_from_excel(EXCEL_PATH, sheet_name=SHEET_NAME)
        print(f"  ✓ Loaded field schema")
        
        print(f"  ✓ Transcript loaded ({len(transcript_text)} characters)")
        
        # Extract reasoning
        print("\n[1.2] Extracting fields (Reasoning step)...")
        extracted_output = extract_all_fields(transcript_text, field_schema)
        print("  ✓ Reasoning extraction complete")
        
        # Save reasoning output
        step1_path = os.path.join(output_dir, "step-1_reasoning.txt")
        with open(step1_path, "w", encoding="utf-8") as f:
            f.write(extracted_output)
        print(f"  ✓ Reasoning saved: {step1_path}")
        
        time.sleep(2)
        
        # Generate final JSON
        print("\n[1.3] Generating final JSON...")
        content = generate_json(extracted_output)
        parsed_json = json.loads(content)
        
        # Save JSON output
        json_output_path = os.path.join(output_dir, json_output_name)
        with open(json_output_path, "w", encoding="utf-8") as f:
            json.dump(parsed_json, f, indent=4, ensure_ascii=False)
        print(f"  ✓ JSON saved: {json_output_path}")
        
        print("\n" + "-" * 60)
        print("FPQ EXTRACTION COMPLETE")
        print("-" * 60)
        
        return json_output_path
        
    except Exception as e:
        print(f"\n  ✗ ERROR during extraction: {str(e)}")
        return None


def run_pdf_generation(json_path: str, output_dir: str) -> Optional[str]:
    """Generate PDF from JSON data using template."""
    print("\n" + "=" * 60)
    print("STEP 2: PDF GENERATION")
    print("=" * 60)
    
    pdf_output_name = "final_output.pdf"
    pdf_output_path = os.path.join(output_dir, pdf_output_name)
    
    # Validate input files
    print("\n[2.1] Validating input files...")
    for name, path in [("JSON", json_path), ("Template", TEMPLATE_PATH)]:
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
        data = load_json_file(json_path)
        print(f"  ✓ Loaded {len(data)} sections")
        
        # Unpack template
        print("\n[2.3] Unpacking template...")
        if not unpack_docx(TEMPLATE_PATH, template_unpacked):
            print("  ✗ Failed to unpack template")
            return None
        print("  ✓ Template unpacked")
        
        # Fill template
        print("\n[2.4] Filling template with data...")
        fill_template(template_unpacked, filled_unpacked, data, TEMPLATE_MAPPING)
        fix_fonts(filled_unpacked)
        print("  ✓ Template filled")
        
        # Pack output (temporary docx)
        print("\n[2.5] Creating intermediate document...")
        temp_docx = os.path.join(work_dir, "temp_output.docx")
        if not pack_docx(filled_unpacked, temp_docx):
            print("  ✗ Failed to pack document")
            return None
        print("  ✓ Intermediate document created")
        
        # Convert to PDF
        print("\n[2.6] Converting to PDF...")
        if not convert_docx_to_pdf(temp_docx, pdf_output_path):
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


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Paraplanner API is running"}


@app.post("/process")
async def process_transcript(
    file: UploadFile = File(..., description="Transcript file (.txt, .vtt, .docx) OR Audio file (.mp3, .wav, .m4a)")
):
    """
    Process a transcript or audio file and generate PDF report.
    
    - If transcript file (.txt, .vtt, .docx) is uploaded: Uses it directly
    - If audio file (.mp3, .wav, .m4a) is uploaded: Transcribes it first using AssemblyAI
    
    Returns:
        - process_id: Unique identifier for this processing job
        - transcript: The transcript text (either uploaded or generated)
        - pdf_filename: Name of the generated PDF file
        - download_url: URL to download the PDF
    """
    process_id = str(uuid.uuid4())
    
    # Create output directory for this process
    output_dir = os.path.join(OUTPUT_DIR, process_id)
    os.makedirs(output_dir, exist_ok=True)
    
    # Determine file type
    filename = file.filename.lower()
    file_extension = os.path.splitext(filename)[1]
    
    # Audio extensions
    audio_extensions = ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.webm']
    # Transcript extensions
    transcript_extensions = ['.txt', '.vtt', '.docx']
    
    try:
        # Save uploaded file
        temp_file_path = os.path.join(output_dir, file.filename)
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        transcript_text = ""
        
        if file_extension in audio_extensions:
            # Audio file - needs transcription
            if not ASSEMBLYAI_API_KEY:
                raise HTTPException(
                    status_code=400,
                    detail="AssemblyAI API key not configured. Cannot transcribe audio."
                )
            
            print(f"Processing audio file: {filename}")
            formatted_transcript, plain_transcript = transcribe_with_diarization(temp_file_path)
            
            if formatted_transcript is None:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to transcribe audio file"
                )
            
            transcript_text = formatted_transcript
            
            # Save transcript
            transcript_path = os.path.join(output_dir, "transcript.txt")
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(formatted_transcript)
                
        elif file_extension in transcript_extensions:
            # Transcript file - use directly
            print(f"Processing transcript file: {filename}")
            transcript_text = read_transcript(temp_file_path)
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_extension}. Supported: {audio_extensions + transcript_extensions}"
            )
        
        # Save transcript to output
        transcript_output_path = os.path.join(output_dir, "transcript.txt")
        with open(transcript_output_path, "w", encoding="utf-8") as f:
            f.write(transcript_text)
        
        # Run FPQ Extraction
        json_output_path = run_fpq_extraction(transcript_text, output_dir)
        
        if json_output_path is None:
            raise HTTPException(
                status_code=500,
                detail="Failed during FPQ extraction step"
            )
        
        # Run PDF Generation
        pdf_output_path = run_pdf_generation(json_output_path, output_dir)
        
        if pdf_output_path is None:
            raise HTTPException(
                status_code=500,
                detail="Failed during PDF generation step"
            )
        
        # Store process info
        pdf_filename = os.path.basename(pdf_output_path)
        processed_files[process_id] = {
            "pdf_path": pdf_output_path,
            "pdf_filename": pdf_filename,
            "transcript_path": transcript_output_path,
            "json_path": json_output_path,
            "created_at": datetime.now().isoformat()
        }
        
        return JSONResponse({
            "status": "success",
            "process_id": process_id,
            "transcript": transcript_text[:2000] + "..." if len(transcript_text) > 2000 else transcript_text,
            "transcript_length": len(transcript_text),
            "pdf_filename": pdf_filename,
            "download_url": f"/download/{process_id}"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}"
        )


@app.get("/download/{process_id}")
async def download_pdf(process_id: str):
    """
    Download the generated PDF file.
    
    Args:
        process_id: The unique identifier returned from /process endpoint
        
    Returns:
        The PDF file as a downloadable attachment
    """
    if process_id not in processed_files:
        # Check if file exists on disk
        potential_path = os.path.join(OUTPUT_DIR, process_id, "final_output.pdf")
        if os.path.exists(potential_path):
            return FileResponse(
                path=potential_path,
                filename="final_output.pdf",
                media_type="application/pdf"
            )
        
        raise HTTPException(
            status_code=404,
            detail=f"Process ID not found: {process_id}"
        )
    
    file_info = processed_files[process_id]
    pdf_path = file_info["pdf_path"]
    
    if not os.path.exists(pdf_path):
        raise HTTPException(
            status_code=404,
            detail="PDF file not found. It may have been deleted."
        )
    
    return FileResponse(
        path=pdf_path,
        filename=file_info["pdf_filename"],
        media_type="application/pdf"
    )


@app.get("/status/{process_id}")
async def get_status(process_id: str):
    """Get the status and info of a processed file"""
    if process_id not in processed_files:
        raise HTTPException(
            status_code=404,
            detail=f"Process ID not found: {process_id}"
        )
    
    return processed_files[process_id]


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
