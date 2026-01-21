"""
Extraction Service
==================
Handles field extraction from transcripts using LLM.
"""
import json
import time
import os
from typing import Dict, Optional
from datetime import datetime
import pandas as pd
from app.config import settings
from app.services.llm_client import llm_client


class ExtractionService:
    """Service for extracting structured data from transcripts."""
    
    def load_field_definitions_from_excel(self) -> Dict[str, Dict[str, str]]:
        """Load field definitions from Excel."""
        print(f"Loading field definitions from {settings.EXCEL_PATH}...")
        
        df = pd.read_excel(settings.EXCEL_PATH, sheet_name=settings.SHEET_NAME)
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
    
    def create_json_schema(self, field_schema: Dict[str, Dict[str, str]]) -> str:
        """Create JSON schema string from field schema."""
        schema_lines = []
        for section, fields in field_schema.items():
            for field_name, metadata in fields.items():
                description = metadata['description']
                schema_line = f'  "{section}" -> "{field_name}" : {description}'
                schema_lines.append(schema_line)
        return '\n'.join(schema_lines)
    
    def extract_all_fields(self, transcript: str, field_schema: Dict[str, Dict[str, str]]) -> str:
        """Extract ALL fields in a SINGLE API call."""
        print(f"Extracting ALL {len(field_schema)} sections in a SINGLE API call...")
        
        current_date = datetime.now().strftime("%d-%B-%Y")
        schema_string = self.create_json_schema(field_schema)
        total_fields = sum(len(fields) for fields in field_schema.values())
        print(f"  Total fields to extract: {total_fields}")
        
        prompt = f"""
You are a financial data extraction assistant. Your task is to extract information SPECIFICALLY FOR THE CLIENT (NOT THE ADVISER) from a financial planning meeting transcript.

================================================================================
TRANSCRIPT:
================================================================================
{transcript}

================================================================================
FIELD SCHEMA WITH BUSINESS RULES:
================================================================================
{schema_string}

================================================================================
SECTION 1: UNDERSTANDING THE TASK
================================================================================

You must extract values for EVERY field listed in the schema above. Each field's description contains its extraction rule, which falls into one of three types:

TYPE A - STATIC VALUE: The description provides the exact value to use
TYPE B - EXTRACT FROM TRANSCRIPT: The description asks you to find information
TYPE C - CONDITIONAL: The description has if/then logic

Process fields IN THE ORDER they appear in the schema. Do not skip any field.

================================================================================
SECTION 2: CLIENT VS ADVISER DISTINCTION (CRITICAL)
================================================================================

Extract only CLIENT information, not adviser's personal details.

INCLUDE (Client-relevant):
✓ Client's personal details, family, employment, health
✓ Spouse/partner details (employment, pension, retirement plans)
✓ Children and grandchildren (education, financial needs, gifts)
✓ Client's assets, income, expenditure, debts, goals
✓ Financial concepts/rules the adviser EXPLAINS to the client

EXCLUDE (Adviser/Firm-related):
✗ Adviser's personal life, health, family, anecdotes
✗ Advisory firm's internal operations (IT issues, cyber attacks)

================================================================================
SECTION 3: HANDLING MULTI-ITEM FIELDS (ARRAYS) - CRITICAL
================================================================================

Three sections contain MULTIPLE ITEMS that must be extracted ITEM-BY-ITEM:

▸ "7. Savings & Investments" → Multiple ASSETS
▸ "9. Protection" → Multiple PRODUCTS  
▸ "12. Goals & Objectives" → Multiple GOALS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ WRONG FORMAT - DO NOT DO THIS (grouping by field):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
---
field_name: [First array field from schema]
Value: Item1; Item2; Item3; Item4
---
field_name: [Second array field from schema]
Value: Item1; Item2; Item3; Item4
---
field_name: [Third array field from schema]
Value: Item1; Item2; Item3; Item4
---

^ THIS IS WRONG because all items are combined into one field with semicolons.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ CORRECT FORMAT - DO THIS (grouping by item):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
---
Asset 1:
  [First array field]: [value for this asset]
  [Second array field]: [value for this asset]
  [Third array field]: [value for this asset]
  [Fourth array field]: [value for this asset]
---
Asset 2:
  [First array field]: [value for this asset]
  [Second array field]: [value for this asset]
  [Third array field]: [value for this asset]
  [Fourth array field]: [value for this asset]
---

^ THIS IS CORRECT because each asset is a complete block with ALL its fields together.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SAME PATTERN FOR PRODUCTS AND GOALS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
---
Product 1:
  [First product field]: [value]
  [Second product field]: [value]
  ...all product fields from schema...
---
Goal 1:
  [First goal field]: [value]
  [Second goal field]: [value]
  ...all goal fields from schema...
---

PROCESS:
1. First extract section-level fields (Soft Notes, Totals) using standard format
2. Identify all distinct items in transcript (assets, products, goals)
3. For EACH item, create a numbered block (Asset 1:, Asset 2:, etc.)
4. Include ALL array fields from the schema for that item within its block

CRITICAL RULE: Never combine multiple items into one field value with semicolons or bullet points.

================================================================================
SECTION 4: SOFT NOTES EXTRACTION REQUIREMENTS
================================================================================

Soft Notes are FREE-TEXT NARRATIVE fields. The VALUE must be COMPREHENSIVE.

Capture ALL of the following if mentioned:
- Monetary amounts, percentages, time periods, counts
- Financial platforms and product names
- Spouse details (employment, pension, retirement timeline)
- Children/grandchildren (education, financial needs)
- Tax rules explained, strategy discussions, constraints
- Future intentions (retirement dates, planned purchases)

FIELD-SPECIFIC FOCUS:
- Personal Details Soft Notes → Employment, lifestyle, family support plans
- Retirement Planning Soft Notes → ALL pension pots (client AND spouse), drawdown strategies
- Savings & Investments Soft Notes → Performance metrics, platforms, interest rates
- Protection Soft Notes → Product types, coverage amounts, premium details
- Estate Planning Soft Notes → Tax rules, trust mechanics, gifts to grandchildren
- Goals & Objectives Soft Notes → All goals for client AND family members

================================================================================
SECTION 5: OUTPUT FORMAT
================================================================================

For EVERY field, output in this format:

---
[Field #X.Y]
Section_name: [Exact section name from schema]
field_name: [Exact field name from schema]
Evidence: [3-4 short quotes - USE 10-15 lines total]
Value: [The extracted value] | Reason: [Brief explanation]
---

**EVIDENCE RULES (STRICT):**
- Evidence is for TRACEABILITY only (proving where you found it)
- USE 10-15 lines, use only 3-4 short quotes (1-2 sentences each)
- Use ellipsis (...) to shorten long quotes
- Comprehensive details go in VALUE, not Evidence
- Example: "pension pot... about 80 or 90,000" | "she's 70 this year"

**VALUE RULES:**
- For Soft Notes: Write comprehensive narrative paragraphs (NOT bullet points)
- For structured fields: Use concise, specific values
- NEVER calculate values - extract only what is explicitly stated

================================================================================
SECTION 6: EXTRACTION PRINCIPLES
================================================================================

1. FIDELITY: Use exact values from transcript. Do not paraphrase numbers.
2. COMPLETENESS: Extract ALL fields. Use "Not found" only when genuinely absent.
3. NO ASSUMPTIONS: Do not infer unstated information.
4. NO CALCULATION: Never compute values (don't convert monthly to yearly, etc.)
5. MULTIPLE PASSES: Re-scan for missed numerical values, family details, concepts.
6. SOFT NOTES: When in doubt, INCLUDE information in the Value field.
7. EVIDENCE DISCIPLINE: Keep Evidence SHORT (10-15 lines max). Details go in Value.

================================================================================
BEGIN EXTRACTION
================================================================================

Process each field in order. Start with Meeting section, then all numbered sections.

Extract now:
"""
        # print('=====')
        # print(prompt)
        # print('=====')
        print("  Sending request to LLM API...")
        response_text = llm_client.invoke(prompt)
        return response_text
    
    def generate_json(self, extracted_json: str) -> str:
        """Convert extracted data to JSON format."""
        prompt = f"""
This is the extracted json:

==============================================
{extracted_json}
==============================================
RULES:

**RULE 1: PRESERVE ALL VALUES EXACTLY**
- For EVERY field in the extraction, copy the "Value:" content EXACTLY as written
- DO NOT paraphrase, summarize, or modify the values
- DO NOT replace an extracted value with "Not found" - if the extraction shows a value, USE THAT VALUE
- If the extraction says "Value: Not found", then and ONLY then use "Not found" in JSON

**RULE 2: INCLUDE EVERY SINGLE FIELD**
- Count the total fields in the extraction above
- Your JSON MUST contain the EXACT same number of fields
- DO NOT skip any field
- DO NOT merge multiple fields into one

**RULE 3: USE EXACT SECTION AND FIELD NAMES**
- Copy section names EXACTLY as they appear (e.g., "1. Personal Details", "7. Savings & Investments")
- Copy field names EXACTLY as they appear (e.g., "Client Name(s)", "Personal Details Soft Notes")
- The section number must match what's in the extraction

**RULE 4: HANDLE ARRAYS CORRECTLY**
For sections with multiple items (Assets, Products, Goals):
- Each "Asset 1:", "Asset 2:", etc. becomes a separate object in the "Assets" array
- Each "Product 1:", "Product 2:", etc. becomes a separate object in the "Products" array  
- Each "Goal 1:", "Goal 2:", etc. becomes a separate object in the "Goals" array


==============================================
STRICTLY : GENERATE A JSON OUT OF THIS IN THIS FORMAT:

{{
  "Meeting": {{
    "<Field Name>": "<Value>",
    "<Field Name>": "<Value>"
  }},
  "<Section Number>. <Section Name>": {{
    "<Field Name>": "<Value>",
    "<Section Name> Soft Notes": "<Narrative summary>"
  }},
  "7. Savings & Investments": {{
    "Total Assets":  "<Value>",
    "Savings & Investments Soft Notes": "<Narrative summary>",
    "Assets": [
      {{
        "<Field Name>": "<Value>", # all fields for Asset 1
        "<Field Name>": "<Value>"
      }},
      {{
        "<Field Name>": "<Value>", # all fields for Asset 2
        "<Field Name>": "<Value>"
      }}
    ]
  }},
  "9. Protection": {{
    "Protection Soft Notes": "<Narrative summary>",
    "Products": [
      {{
        "<Field Name>": "<Value>", # all fields for products 1
        "<Field Name>": "<Value>"
      }},
      {{
        "<Field Name>": "<Value>", # all fields for products 1
        "<Field Name>": "<Value>"
      }}
    ]
  }},
  "12. Goals & Objectives": {{
    "Goals & Objectives Soft Notes": "<Narrative summary>",
    "Goals": [
      {{
        "<Field Name>": "<Value>", # all fields for goal 1
        "<Field Name>": "<Value>"
      }},
       {{
        "<Field Name>": "<Value>", # all fields for goal 1
        "<Field Name>": "<Value>"
      }}
    ]
  }}
}}

==============================================
VALIDATION CHECKLIST (do this before outputting):
==============================================
☐ Did I include EVERY field from the extraction?
☐ Did I use the EXACT value from each field (not summarized)?
☐ Did I keep section numbers exactly as in extraction?
☐ For array sections, did I create separate objects for each item?
☐ Did I avoid putting "Not found" for fields that have values in extraction?

==============================================
FORMAT REQUIREMENTS:
==============================================
- Output ONLY valid JSON (no markdown, no explanation)
- Use double quotes for all keys and string values
- No trailing commas
- No comments in the JSON
- Start with {{ and end with }}

OUTPUT THE JSON NOW:
"""

        print("Sending request to LLM API...")
        response_text = llm_client.invoke(prompt)

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
    
    def run_extraction(self, transcript_text: str, output_dir: str) -> Optional[str]:
        """Extract data from transcript and generate JSON output."""
        print("\n" + "=" * 60)
        print("STEP 1: FPQ EXTRACTION")
        print("=" * 60)
        
        json_output_name = "final_output.json"
        
        try:
            # Load field definitions
            print("\n[1.1] Loading field definitions from Excel...")
            field_schema = self.load_field_definitions_from_excel()
            print(f"  ✓ Loaded field schema")
            
            print(f"  ✓ Transcript loaded ({len(transcript_text)} characters)")
            
            # Extract reasoning
            print("\n[1.2] Extracting fields (Reasoning step)...")
            extracted_output = self.extract_all_fields(transcript_text, field_schema)
            print("  ✓ Reasoning extraction complete")
            
            # Save reasoning output
            step1_path = os.path.join(output_dir, "step-1_reasoning.txt")
            with open(step1_path, "w", encoding="utf-8") as f:
                f.write(extracted_output)
            print(f"  ✓ Reasoning saved: {step1_path}")
            
            time.sleep(2)
            
            # Generate final JSON
            print("\n[1.3] Generating final JSON...")
            content = self.generate_json(extracted_output)
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


# Global instance
extraction_service = ExtractionService()