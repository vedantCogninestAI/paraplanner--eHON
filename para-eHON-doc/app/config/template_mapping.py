"""
Template Mapping Configuration
==============================
Defines the mapping between JSON data and template placeholders.
"""

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