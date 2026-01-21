# Paraplanner FastAPI Application

A FastAPI application that processes financial transcripts and generates PDF reports.

## Features

- **API Endpoints:**
  - `GET /` - Health check
  - `POST /process` - Process transcript/audio and generate PDF
  - `GET /download/{process_id}` - Download the generated PDF
  - `GET /status/{process_id}` - Check processing status

- **Supported Input Types:**
  - Transcript files: `.txt`, `.vtt`, `.docx`
  - Audio files: `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`, `.webm` (requires AssemblyAI)

## Project Structure
```
Transcript-Flow/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI entry point
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py         # Environment configuration
│   │   └── template_mapping.py # Template placeholders mapping
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm_client.py       # LLM API wrapper
│   │   ├── transcript_service.py
│   │   ├── extraction_service.py
│   │   └── pdf_service.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── xml_helpers.py
│   │   └── text_formatters.py
│   └── apis/
│       ├── __init__.py
│       └── process.py          # API routes
├── files/                      # Template files
│   ├── Paraplanner_Extraction and Rules_v2.xlsx
│   └── latest_but_modifie.docx
├── outputs/                    # Generated files
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .env                        # Create from .env.example
├── .gitignore
└── README.md
```

## Quick Start with Docker

### 1. Clone and Setup
```bash
cd Transcript-Flow

# Copy environment file and fill in your values
cp .env.example .env
```

### 2. Edit .env

Fill in your actual API keys:
```env
MODEL_NAME=your-model-name
DAILOQA_LLM_BASE_URL=https://your-llm-api-url.com
DAILOQA_LLM_API_KEY=your-api-key-here
ASSEMBLYAI_API_KEY=your-assemblyai-api-key
```

### 3. Add Template Files

Place your template files in the `files/` directory:
- `Paraplanner_Extraction and Rules_v2.xlsx`
- `latest_but_modifie.docx`

### 4. Run with Docker
```bash
# Build and start
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

### 5. Access the API

- API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Usage

### Process a Transcript
```bash
curl -X POST "http://localhost:8000/process" \
  -F "file=@transcript.txt"
```

**Response:**
```json
{
  "status": "success",
  "process_id": "uuid-here",
  "transcript": "...",
  "transcript_length": 12345,
  "pdf_filename": "final_output.pdf",
  "download_url": "/download/uuid-here"
}
```

### Download Generated PDF
```bash
curl -O "http://localhost:8000/download/{process_id}"
```

### Check Status
```bash
curl "http://localhost:8000/status/{process_id}"
```

## Local Development (without Docker)

### 1. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install LibreOffice (for PDF conversion)
```bash
# Ubuntu/Debian
sudo apt install libreoffice

# macOS
brew install libreoffice
```

### 4. Run the Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Docker Commands
```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f

# Rebuild after changes
docker-compose up --build

# Remove everything (including volumes)
docker-compose down -v
```

## Output Files

Generated files are stored in `outputs/{process_id}/`:
- `transcript.txt` - The input transcript
- `step-1_reasoning.txt` - LLM extraction reasoning
- `final_output.json` - Extracted structured data
- `final_output.pdf` - Generated PDF report

## Notes

- PDF conversion uses LibreOffice (headless mode)
- Audio transcription requires a valid AssemblyAI API key
- The `files/` directory must contain the Excel and DOCX template files
```

---

## Final Folder Structure
```
Transcript-Flow/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   └── template_mapping.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm_client.py
│   │   ├── transcript_service.py
│   │   ├── extraction_service.py
│   │   └── pdf_service.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── xml_helpers.py
│   │   └── text_formatters.py
│   └── apis/
│       ├── __init__.py
│       └── process.py
├── files/
│   ├── Paraplanner_Extraction and Rules_v2.xlsx
│   └── latest_but_modifie.docx
├── outputs/
│   └── .gitkeep
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .env                    # You create this
├── .gitignore
└── README.md