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
Before extracting, identify who is the ADVISER and who is the CLIENT from conversation context (speakers may be labeled as "Speaker A", "Speaker B" or similar generic labels):
- ADVISER: Gives financial advice/suggestions, asks probing questions, explains concepts, mentions firm/compliance matters
- CLIENT: Shares personal/financial details, answers questions about their life/health/family, seeks advice
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

- **Executive Summary field** : Summarize the MEETING OBJECTIVE, KEY DISCUSSIONS, AND PRIMARY ACTIONS RECOMMENDED. Do NOT include adviser personal details.

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
        # print('=====')
        # print(prompt)
        # print('=====')
        print("  Sending request to LLM API...")
        response_text = llm_client.invoke(prompt)
        return response_text
    
    def generate_json(self, extracted_json: str) -> str:
        """Convert extracted data to JSON format."""
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
4. Do not add reason/evidence here. Strictly only field values.

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