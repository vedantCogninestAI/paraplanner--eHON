"""
Application Settings
====================
Central configuration management using environment variables.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    def __init__(self):
        # LLM Configuration
        self.MODEL_NAME = os.getenv("MODEL_NAME")
        self.LLM_BASE_URL = os.getenv("DAILOQA_LLM_BASE_URL")
        self.LLM_API_KEY = os.getenv("DAILOQA_LLM_API_KEY")
        
        # AssemblyAI Configuration
        self.ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
        
        # File paths
        self.BASE_DIR = Path(__file__).resolve().parent.parent.parent
        self.EXCEL_PATH = os.getenv(
            "EXCEL_PATH", 
            str(self.BASE_DIR / "files" / "Paraplanner_Extraction and Rules_v2.xlsx")
        )
        self.SHEET_NAME = os.getenv("SHEET_NAME", "Extraction Fields_JSON")
        self.TEMPLATE_PATH = os.getenv(
            "TEMPLATE_PATH", 
            str(self.BASE_DIR / "files" / "latest_but_modifie.docx")
        )
        self.OUTPUT_DIR = os.getenv(
            "OUTPUT_DIR", 
            str(self.BASE_DIR / "outputs")
        )
        
        # Create output directory if it doesn't exist
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
    
    def validate(self) -> list:
        """Validate required settings and return list of missing ones."""
        missing = []
        if not self.MODEL_NAME:
            missing.append("MODEL_NAME")
        if not self.LLM_BASE_URL:
            missing.append("DAILOQA_LLM_BASE_URL")
        if not self.LLM_API_KEY:
            missing.append("DAILOQA_LLM_API_KEY")
        return missing


# Global settings instance
settings = Settings()