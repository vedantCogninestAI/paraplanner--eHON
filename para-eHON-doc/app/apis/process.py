import os
import uuid
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from app.config import settings
from app.services import transcript_service, extraction_service, pdf_service

# Create router
router = APIRouter()

# Store for tracking processed files (in-memory)
processed_files: Dict[str, dict] = {}


@router.post("/process")
async def process_transcript(
    file: UploadFile = File(..., description="Transcript (.txt, .vtt, .docx), Audio (.mp3, .wav), or Video (.mp4, .mkv) file")
):
    process_id = str(uuid.uuid4())
    
    # Use settings instead of direct variable
    output_dir = os.path.join(settings.OUTPUT_DIR, process_id)
    os.makedirs(output_dir, exist_ok=True)
    
    filename = file.filename.lower()
    file_extension = os.path.splitext(filename)[1]
    
    audio_extensions = transcript_service.get_supported_audio_extensions()
    video_extensions = transcript_service.get_supported_video_extensions()
    transcript_extensions = transcript_service.get_supported_transcript_extensions()
    
    try:
        temp_file_path = os.path.join(output_dir, file.filename)
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        transcript_text = ""
        
        if file_extension in video_extensions:
            # Video file - extract audio first, then transcribe
            if not settings.ASSEMBLYAI_API_KEY:
                raise HTTPException(
                    status_code=400,
                    detail="AssemblyAI API key not configured."
                )
            
            print(f"Processing video file: {filename}")
            
            # Extract audio from video
            audio_path = transcript_service.extract_audio_from_video(temp_file_path, output_dir)
            
            if audio_path is None:
                raise HTTPException(status_code=500, detail="Failed to extract audio from video")
            
            # Transcribe the extracted audio
            formatted_transcript, _ = transcript_service.transcribe_audio(audio_path)
            
            if formatted_transcript is None:
                raise HTTPException(status_code=500, detail="Failed to transcribe audio")
            
            transcript_text = formatted_transcript
        
        elif file_extension in audio_extensions:
            # Audio file - transcribe directly
            if not settings.ASSEMBLYAI_API_KEY:
                raise HTTPException(
                    status_code=400,
                    detail="AssemblyAI API key not configured."
                )
            
            print(f"Processing audio file: {filename}")
            formatted_transcript, _ = transcript_service.transcribe_audio(temp_file_path)
            
            if formatted_transcript is None:
                raise HTTPException(status_code=500, detail="Failed to transcribe audio")
            
            transcript_text = formatted_transcript
                
        elif file_extension in transcript_extensions:
            # Transcript file - use directly
            print(f"Processing transcript file: {filename}")
            transcript_text = transcript_service.read_transcript(temp_file_path)
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_extension}. Supported: {transcript_extensions + audio_extensions + video_extensions}"
            )
        
        # Save transcript
        transcript_output_path = os.path.join(output_dir, "transcript.txt")
        with open(transcript_output_path, "w", encoding="utf-8") as f:
            f.write(transcript_text)
        
        # Use service methods
        json_output_path = extraction_service.run_extraction(transcript_text, output_dir)
        
        if json_output_path is None:
            raise HTTPException(status_code=500, detail="Failed during extraction")
        
        pdf_output_path = pdf_service.run_generation(json_output_path, output_dir)
        
        if pdf_output_path is None:
            raise HTTPException(status_code=500, detail="Failed during PDF generation")
        
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
            "transcript": transcript_text,
            "transcript_length": len(transcript_text),
            "pdf_filename": pdf_filename,
            "pdf_preview_url": f"/static/outputs/{process_id}/final_output.pdf",  # ✅ This works
            "download_url": f"/download/{process_id}"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.get("/download/{process_id}")
async def download_pdf(process_id: str):
    if process_id not in processed_files:
        potential_path = os.path.join(settings.OUTPUT_DIR, process_id, "final_output.pdf")
        if os.path.exists(potential_path):
            return FileResponse(path=potential_path, filename="final_output.pdf", media_type="application/pdf")
        
        raise HTTPException(status_code=404, detail=f"Process ID not found: {process_id}")
    
    file_info = processed_files[process_id]
    pdf_path = file_info["pdf_path"]
    
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    return FileResponse(path=pdf_path, filename=file_info["pdf_filename"], media_type="application/pdf")


@router.get("/status/{process_id}")
async def get_status(process_id: str):
    if process_id not in processed_files:
        raise HTTPException(status_code=404, detail=f"Process ID not found: {process_id}")
    
    return processed_files[process_id]
