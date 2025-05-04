from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import os
import argparse
from caption_analyzer import analyze_caption
from audio_transcriber import transcribe_audio
from dotenv import load_dotenv
import tempfile
import re

# Load environment variables from .env file
load_dotenv()

# Define your constants
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.readonly'
]
SERVICE_ACCOUNT_FILE = 'service-account.json'
FOLDER_ID = '1urUZgHEsiD2m84o0mRwABx98Hx4zVoRx'
SHARED_DRIVE_ID = '0AC-zpP62xFGzUk9PVA'

# Supported file extensions
TEXT_EXTENSIONS = ['.txt']
AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a']

def get_google_drive_service():
    """Initialize and return Google Drive service."""
    try:
        # Make sure we're using the full drive scope
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"Error initializing Google Drive service: {str(e)}")
        return None

def download_file_content(service, file_id: str) -> str:
    """Download and return the content of a file from Google Drive."""
    try:
        request = service.files().get_media(fileId=file_id)
        file_content = io.BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        return file_content.getvalue().decode('utf-8')
    except Exception as e:
        print(f"Error downloading file: {str(e)}")
        return None

def download_file_to_local(service, file_id: str) -> str:
    """Download a file from Google Drive to a local temporary file."""
    try:
        # Get file metadata to determine the file name
        file_metadata = service.files().get(
            fileId=file_id, 
            fields="name, mimeType",
            supportsAllDrives=True
        ).execute()
        
        file_name = file_metadata.get('name', 'downloaded_file')
        
        # Create tmp directory if it doesn't exist
        tmp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tmp')
        os.makedirs(tmp_dir, exist_ok=True)
        
        # Create a file with the same extension as the original
        _, file_extension = os.path.splitext(file_name)
        temp_path = os.path.join(tmp_dir, f"{file_id}{file_extension}")
        
        # Download the file
        request = service.files().get_media(fileId=file_id)
        with open(temp_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        
        print(f"Downloaded file to: {temp_path}")
        return temp_path
    except Exception as e:
        print(f"Error downloading file: {str(e)}")
        return None

def extract_file_id_from_link(link: str) -> str:
    """Extract file ID from a Google Drive link."""
    # Pattern for standard Google Drive file links
    pattern = r'https://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)'
    match = re.search(pattern, link)
    if match:
        return match.group(1)
    
    # Pattern for Google Drive sharing links
    pattern = r'https://drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)'
    match = re.search(pattern, link)
    if match:
        return match.group(1)
    
    # If the input is already a file ID (no URL pattern found)
    if re.match(r'^[a-zA-Z0-9_-]+$', link):
        return link
    
    print(f"Error: Could not extract file ID from link: {link}")
    return None

def is_text_file(file_path: str) -> bool:
    """Check if the file is a text file based on its extension."""
    _, ext = os.path.splitext(file_path.lower())
    return ext in TEXT_EXTENSIONS

def is_audio_file(file_path: str) -> bool:
    """Check if the file is an audio file based on its extension."""
    _, ext = os.path.splitext(file_path.lower())
    return ext in AUDIO_EXTENSIONS

def process_file(file_path_or_id, is_drive_file=False):
    """Process a file either from local path or Google Drive."""
    try:
        # Get OpenAI API key from environment variable
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            print("Error: OPENAI_API_KEY environment variable not set")
            return
        
        # Initialize variables
        content = None
        file_name = None
        temp_file_path = None
        
        if is_drive_file:
            # Get Google Drive service
            service = get_google_drive_service()
            
            # Download the file from Google Drive
            temp_file_path = download_file_to_local(service, file_path_or_id)
            if not temp_file_path:
                print(f"Failed to download file with ID: {file_path_or_id}")
                return
            
            # Get the file name from the path
            file_name = os.path.basename(temp_file_path)
            
            # Check file type and process accordingly
            if is_text_file(temp_file_path):
                # Read the content of the downloaded text file
                with open(temp_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            elif is_audio_file(temp_file_path):
                # Transcribe the audio file
                print(f"Transcribing audio file: {file_name}")
                result = transcribe_audio(openai_api_key, temp_file_path)
                if result["success"]:
                    content = result["transcription"]
                    print("Transcription completed successfully.")
                else:
                    print(f"Error transcribing audio: {result.get('error', 'Unknown error occurred')}")
                    return
            else:
                print(f"Unsupported file type: {file_name}")
                return
        else:
            # Check if the local file exists
            if not os.path.exists(file_path_or_id):
                print(f"Error: File not found: {file_path_or_id}")
                return
            
            # Get the file name from the path
            file_name = os.path.basename(file_path_or_id)
            
            # Check file type and process accordingly
            if is_text_file(file_path_or_id):
                # Read the content of the local text file
                with open(file_path_or_id, 'r', encoding='utf-8') as f:
                    content = f.read()
            elif is_audio_file(file_path_or_id):
                # Transcribe the audio file
                print(f"Transcribing audio file: {file_name}")
                result = transcribe_audio(openai_api_key, file_path_or_id)
                if result["success"]:
                    content = result["transcription"]
                    print("Transcription completed successfully.")
                else:
                    print(f"Error transcribing audio: {result.get('error', 'Unknown error occurred')}")
                    return
            else:
                print(f"Unsupported file type: {file_name}")
                return
        
        # Analyze the content
        print(f"Analyzing content from: {file_name}")
        result = analyze_caption(openai_api_key, content)
        
        if result["success"]:
            print(f"\nAnalysis for {file_name}:")
            print(result["analysis"])
        else:
            print(f"\nError analyzing {file_name}: {result.get('error', 'Unknown error occurred')}")
        
        # Clean up temporary file if it was created
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            print(f"Cleaned up temporary file: {temp_file_path}")
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        # Clean up temporary file if it was created
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            print(f"Cleaned up temporary file: {temp_file_path}")

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Analyze caption files or transcribe audio files')
    parser.add_argument('--file', '-f', help='Path to a local file to analyze (text or audio)')
    parser.add_argument('--drive-file', '-d', help='ID or link of a Google Drive file to analyze (text or audio)')
    args = parser.parse_args()
    
    # Get OpenAI API key from environment variable
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        return
    
    # Process based on arguments
    if args.file:
        # Process a local file
        print(f"Processing local file: {args.file}")
        process_file(args.file, is_drive_file=False)
    
    elif args.drive_file:
        # Process a Google Drive file
        file_id = extract_file_id_from_link(args.drive_file)
        if file_id:
            print(f"Processing Google Drive file with ID: {file_id}")
            process_file(file_id, is_drive_file=True)
        else:
            print("Error: Invalid Google Drive link or file ID")
    
    else:
        # No arguments provided, show usage
        parser.print_help()

if __name__ == "__main__":
    main()
