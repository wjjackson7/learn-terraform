from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import tempfile
from typing import Optional, Dict, Any
from audio_transcriber import transcribe_audio
from caption_analyzer import analyze_caption
from main import get_google_drive_service, download_file_to_local, extract_file_id_from_link

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Audio Processing API",
    description="API for audio transcription and text analysis",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Pydantic models for request/response validation
class TranscriptionResponse(BaseModel):
    success: bool
    transcription: Optional[str] = None
    error: Optional[str] = None

class AnalysisResponse(BaseModel):
    success: bool
    analysis: Optional[str] = None
    error: Optional[str] = None

class DriveFileRequest(BaseModel):
    file_id_or_link: str

@app.get("/")
async def root():
    """
    Root endpoint for basic connectivity test.
    """
    return {"message": "Welcome to the Audio Processing API"}

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    try:
        # Check OpenAI API key
        openai_api_key = os.getenv('OPENAI_API_KEY')
        openai_configured = bool(openai_api_key)
        
        # Check Google Drive service
        drive_service = get_google_drive_service()
        drive_configured = bool(drive_service)
        
        return {
            "status": "healthy",
            "openai_configured": openai_configured,
            "drive_configured": drive_configured,
            "temp_dir_writable": os.access(tempfile.gettempdir(), os.W_OK)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.get("/debug/env")
async def debug_environment():
    """
    Debug endpoint to check environment variables.
    """
    return {
        "openai_key_set": bool(os.getenv('OPENAI_API_KEY')),
        "temp_dir": tempfile.gettempdir(),
        "working_dir": os.getcwd(),
        "python_path": os.getenv('PYTHONPATH')
    }

@app.post("/transcribe/upload", response_model=TranscriptionResponse)
async def transcribe_uploaded_file(file: UploadFile = File(...)):
    """
    Transcribe an uploaded audio file.
    """
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        # Get OpenAI API key
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")

        # Transcribe the audio
        result = transcribe_audio(openai_api_key, temp_path)

        # Clean up temporary file
        os.unlink(temp_path)

        return result

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}\n\nDetails:\n{error_details}")

@app.post("/transcribe/drive", response_model=TranscriptionResponse)
async def transcribe_drive_file(request: DriveFileRequest):
    """
    Transcribe an audio file from Google Drive.
    """
    try:
        # Get OpenAI API key
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")

        # Extract file ID from link if necessary
        file_id = extract_file_id_from_link(request.file_id_or_link)
        if not file_id:
            raise HTTPException(status_code=400, detail="Invalid file ID or link")

        # Get Google Drive service
        service = get_google_drive_service()
        if not service:
            raise HTTPException(status_code=500, detail="Failed to initialize Google Drive service")

        # Download the file
        temp_path = download_file_to_local(service, file_id)
        if not temp_path:
            raise HTTPException(status_code=404, detail="File not found in Google Drive")

        # Transcribe the audio
        result = transcribe_audio(openai_api_key, temp_path)

        # Clean up temporary file
        os.unlink(temp_path)

        return result

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}\n\nDetails:\n{error_details}")

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_text(text: str = Form(...)):
    """
    Analyze text content.
    """
    try:
        # Get OpenAI API key
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")

        # Analyze the text
        result = analyze_caption(openai_api_key, text)
        return result

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}\n\nDetails:\n{error_details}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 