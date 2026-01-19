# Paraplanner FastAPI Application

A FastAPI application that processes financial transcripts and generates PDF reports.

## Features

- **Two API Endpoints:**
  1. `POST /process` - Process transcript/audio and generate PDF
  2. `GET /download/{process_id}` - Download the generated PDF

- **Supported Input Types:**
  - Transcript files: `.txt`, `.vtt`, `.docx`
  - Audio files: `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`, `.webm` (requires AssemblyAI)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:
- `LITELLM_API_KEY` - Your Dailoqa API key
- `ASSEMBLYAI_API_KEY` - Your AssemblyAI API key (for audio transcription)

### 3. Prepare Required Files

Create a `files` directory and add:
- `Paraplanner_Extraction and Rules_v2.xlsx` - Field definitions Excel file
- `latest_but_modifie.docx` - PDF template file

```bash
mkdir -p files
# Copy your Excel and template files to the files directory
```

### 4. Run the Server

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## API Usage

### Process Transcript/Audio

**Endpoint:** `POST /process`

**Request:** Upload a file (transcript or audio)

```bash
# With transcript file
curl -X POST "http://localhost:8000/process" \
  -F "file=@transcript.txt"

# With audio file
curl -X POST "http://localhost:8000/process" \
  -F "file=@recording.mp3"
```

**Response:**
```json
{
  "status": "success",
  "process_id": "uuid-here",
  "transcript": "First 2000 characters of transcript...",
  "transcript_length": 12345,
  "pdf_filename": "final_output.pdf",
  "download_url": "/download/uuid-here"
}
```

### Download PDF

**Endpoint:** `GET /download/{process_id}`

```bash
curl -O "http://localhost:8000/download/{process_id}"
```

### Check Status

**Endpoint:** `GET /status/{process_id}`

```bash
curl "http://localhost:8000/status/{process_id}"
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Directory Structure

```
paraplanner_api/
├── main.py              # Main FastAPI application
├── requirements.txt     # Python dependencies
├── .env.example         # Example environment variables
├── .env                 # Your actual environment variables (create this)
├── files/               # Required input files
│   ├── Paraplanner_Extraction and Rules_v2.xlsx
│   └── latest_but_modifie.docx
└── outputs/             # Generated output files (auto-created)
    └── {process_id}/
        ├── transcript.txt
        ├── step-1_reasoning.txt
        ├── final_output.json
        └── final_output.pdf
```

## Notes

- On Windows, PDF conversion uses `docx2pdf` (requires Microsoft Word)
- On Linux, PDF conversion uses LibreOffice (install with `apt install libreoffice`)
- Audio transcription requires a valid AssemblyAI API key
- The application uses the exact same logic as your Jupyter notebook
