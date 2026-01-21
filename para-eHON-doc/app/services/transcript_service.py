"""
Transcript Service
==================
Handles reading and processing various transcript formats.
"""
import os
import re
import subprocess
from typing import Tuple, Optional
from docx import Document
import assemblyai as aai
from app.config import settings


class TranscriptService:
    """Service for handling transcript files and audio transcription."""
    
    def __init__(self):
        # Initialize AssemblyAI if key is available
        if settings.ASSEMBLYAI_API_KEY:
            aai.settings.api_key = settings.ASSEMBLYAI_API_KEY
    
    def extract_audio_from_video(self, video_path: str, output_dir: str) -> Optional[str]:
        """Extract audio from video file using ffmpeg."""
        print(f"Extracting audio from video: {video_path}")
        
        # Create output audio path
        video_filename = os.path.basename(video_path)
        audio_filename = os.path.splitext(video_filename)[0] + ".mp3"
        audio_path = os.path.join(output_dir, audio_filename)
        
        try:
            # Run ffmpeg to extract audio
            subprocess.run([
                'ffmpeg',
                '-i', video_path,        # Input video
                '-vn',                    # No video
                '-acodec', 'libmp3lame', # MP3 codec
                '-q:a', '2',             # Quality (0-9, 2 is good)
                '-y',                     # Overwrite output
                audio_path
            ], check=True, capture_output=True)
            
            print(f"  ✓ Audio extracted: {audio_path}")
            return audio_path
            
        except subprocess.CalledProcessError as e:
            print(f"  ✗ Failed to extract audio: {e.stderr.decode()}")
            return None
        except Exception as e:
            print(f"  ✗ Error extracting audio: {str(e)}")
            return None
    
    def transcribe_audio(self, audio_path: str) -> Tuple[Optional[str], Optional[str]]:
        """Transcribe audio with speaker diarization using AssemblyAI."""
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
    
    def read_docx(self, docx_path: str) -> str:
        """Read transcript from a DOCX file."""
        doc = Document(docx_path)
        transcript_text = []
        for para in doc.paragraphs:
            if para.text.strip():
                transcript_text.append(para.text)
        return '\n'.join(transcript_text)
    
    def read_vtt(self, vtt_path: str) -> str:
        """Read transcript from a VTT (WebVTT) file."""
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
    
    def read_txt(self, txt_path: str) -> str:
        """Read transcript from a plain text file."""
        with open(txt_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def read_transcript(self, file_path: str) -> str:
        """Read transcript based on file extension."""
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.docx':
            print(f"Reading DOCX file: {file_path}")
            return self.read_docx(file_path)
        elif file_extension == '.vtt':
            print(f"Reading VTT file: {file_path}")
            return self.read_vtt(file_path)
        elif file_extension == '.txt':
            print(f"Reading TXT file: {file_path}")
            return self.read_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}. Supported: .docx, .vtt, .txt")
    
    @staticmethod
    def get_supported_audio_extensions() -> list:
        """Return list of supported audio file extensions."""
        return ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.webm']
    
    @staticmethod
    def get_supported_video_extensions() -> list:
        """Return list of supported video file extensions."""
        return ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm']
    
    @staticmethod
    def get_supported_transcript_extensions() -> list:
        """Return list of supported transcript file extensions."""
        return ['.txt', '.vtt', '.docx']


# Global instance
transcript_service = TranscriptService()