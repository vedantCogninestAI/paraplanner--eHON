# =============================================================================
# TEMPLATE MAPPING CONFIG - MATCHES JSON OUTPUT EXACTLY
# =============================================================================

TEMPLATE_MAPPING = {
    "version": "3.0",
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
            "Taxation",
            "Protection",
            "Estate Planning",
            "Attitude to Risk",
            "Goals & Objectives"
        ],
        "Actions & Recommendations": [
            "Immediate",
            "Medium-Term",
            "Long-Term"
        ]
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
                "Client ID",
                "Client Name(s)",
                "Date of Birth",
                "Age",
                "Marital Status",
                "Family Members",
                "No of Dependents",
                "Country of Residence",
                "UK Resident for Tax",
                "UK Domicile",
                "Address",
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
                "State of Health",
                "Long-term Vulnerabilities",
                "Long-term Vulnerabilities Details",
                "Circumstantial Vulnerabilities",
                "Circumstantial Vulnerabilities Details"
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
                "Income Required in Retirement",
                "Cashflow Scenarios & Assumptions",
                "Outcomes & Client Decisions"
            ],
            "is_split_placeholder": False
        },

        "Income & Expenditure": {
            "json_key": "5. Income & Expenditure",
            "soft_notes_placeholder": "[Income & Expenditure Soft Notes]",
            "soft_notes_field": "Income Soft Notes",
            "soft_notes_field_2": "Expenditure Soft Notes",
            "hard_facts_placeholder": "[Income & Expenditure]",
            "hard_facts_fields": [
                "Total Net Monthly Income",
                "Monthly Surplus Income",
                "Total Monthly Expenditure",
                "Mortgages & Rent",
                "Loans & Credit",
                "Pensions, Savings & Insurance",
                "Household & Utilities",
                "Travel & Transport",
                "Discretionary & Leisure",
                "Child Care",
                "All Household Expenditure"
            ],
            "is_split_placeholder": False
        },

        "Loans & Liabilities": {
            "json_key": "6. Loans & Liabilities",
            "soft_notes_placeholder": "[Loans & Liabilities Soft Notes]",
            "soft_notes_field": "Loans & Liabilities Soft Notes",
            "hard_facts_placeholder": "[Loans & Liabilities]",
            "hard_facts_fields": [
                "Total Liabilities",
                "Mortgage (Main Residence)",
                "Mortgage (Other Property)",
                "Credit Cards",
                "Overdraft",
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
                "Asset Product Type",
                "Asset Fund Name",
                "Asset Provider Name",
                "Total Net Worth"
            ],
            "array_field": "Assets",
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
            "hard_facts_fields": [],
            "array_field": "Products",
            "is_split_placeholder": False
        },

        "Estate Planning": {
            "json_key": "10. Estate Planning",
            "soft_notes_placeholder": "[Estate Planning Soft Notes]",
            "soft_notes_field": "Estate Planning Soft Notes",
            "hard_facts_placeholder": "[Estate Planning]",
            "hard_facts_fields": [
                "Estate Value",
                "Have you made a Will",
                "Are your Wills up to date",
                "Powers of Attourney (POA)",
                "Inheritance Tax Liability",
                "Gifting Strategy",
                "Trusts & ISAs",
                "Recommendations or Referrals"
            ],
            "is_split_placeholder": False
        },

        "Attitude to Risk": {
            "json_key": "11. Attitude to Risk",
            "soft_notes_placeholder": "[Attitude to Risk Soft Notes]",
            "soft_notes_field": "Attitude to Risk Soft Notes",
            "hard_facts_placeholder": "[Attitude to Risk]",
            "hard_facts_fields": [
                "Risk Score",
                "Client Risk Category",
                "Agreed Client Risk Category",
                "Capacity for Loss",
                "Knowledge & Experience",
                "Ethical Preference & Other Considerations"
            ],
            "is_split_placeholder": False
        },

        "Goals & Objectives": {
            "json_key": "12. Goals & Objectives",
            "soft_notes_placeholder": "[Goals & Objectives Soft Notes]",
            "soft_notes_field": "Goals & Objectives Soft Notes",
            "hard_facts_placeholder": "[Goals & Objectives]",
            "hard_facts_fields": [
                "Assumed Real Return",
                "Target Annual Income"
            ],
            "array_field": "Goals",
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
# END CONFIG
# =============================================================================