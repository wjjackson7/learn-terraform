from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
import io
import re
from dotenv import load_dotenv
import tempfile
import json
import argparse
from main import (
    get_google_drive_service, 
    download_file_to_local, 
    is_audio_file, 
    process_file,
    AUDIO_EXTENSIONS,
    TEXT_EXTENSIONS
)

# Load environment variables from .env file
load_dotenv()

# Define your constants
SCOPES = ['https://www.googleapis.com/auth/drive']  # Need write access to upload files
SERVICE_ACCOUNT_FILE = 'service-account.json'
OUTPUT_FILE_AFFIX = '_TRANSCRIPT'
OUTPUT_FILE_EXTENSION = '.json'

def list_files_in_folder(service, folder_id, file_types=None):
    """List all files in a Google Drive folder."""
    query = f"'{folder_id}' in parents and trashed = false"
    
    if file_types:
        # Create a query to filter by file extensions
        extension_query = " or ".join([f"name contains '{ext}'" for ext in file_types])
        query += f" and ({extension_query})"
    
    results = []
    page_token = None
    
    while True:
        try:
            response = service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name, mimeType, parents)',
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            results.extend(response.get('files', []))
            page_token = response.get('nextPageToken')
            
            if not page_token:
                break
                
        except Exception as e:
            print(f"Error listing files: {str(e)}")
            break
    
    return results

def get_file_parent_folder(service, file_id):
    """Get the parent folder ID of a file."""
    try:
        file_metadata = service.files().get(
            fileId=file_id,
            fields="parents",
            supportsAllDrives=True
        ).execute()
        
        parents = file_metadata.get('parents', [])
        if parents:
            return parents[0]
        return None
    except Exception as e:
        print(f"Error getting parent folder: {str(e)}")
        return None

def get_processed_files_map(service, folder_id):
    """Get a map of all processed files in a folder by checking JSON files once."""
    processed_files = {}
    try:
        # List all files in the folder
        query = f"'{folder_id}' in parents and mimeType = 'application/json' and trashed = false"
        response = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            supportsAllDrives=True
        ).execute()
        
        files = response.get('files', [])
        
        # Check each JSON file
        for file in files:
            temp_file_path = download_file_to_local(service, file['id'])
            if temp_file_path:
                try:
                    with open(temp_file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if 'original_file' in data:
                            processed_files[data['original_file']] = file['name']
                except Exception as e:
                    print(f"Error reading JSON file {file['name']}: {str(e)}")
                finally:
                    # Clean up the temporary file
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
        
        return processed_files
    except Exception as e:
        print(f"Error getting processed files map: {str(e)}")
        return {}

def check_if_processed_file_exists(processed_files_map, file_name):
    """Check if a file has already been processed using the cached map."""
    if file_name in processed_files_map:
        print(f"Found existing transcription for {file_name} in {processed_files_map[file_name]}")
        return True
    return False

def upload_file_to_drive(service, file_path, parent_folder_id, filename):
    """Upload a file to Google Drive."""
    try:
        file_metadata = {
            'name': filename,
            'parents': [parent_folder_id]
        }
        
        media = MediaFileUpload(
            file_path,
            resumable=True
        )
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id',
            supportsAllDrives=True
        ).execute()
        
        print(f"File uploaded: {filename} (ID: {file.get('id')})")
        return file.get('id')
    except Exception as e:
        print(f"Error uploading file: {str(e)}")
        # Print more detailed error information
        import traceback
        traceback.print_exc()
        return None

def process_audio_file(service, file_id, file_name):
    """Process an audio file and save the output."""
    try:
        # Download the file
        temp_file_path = download_file_to_local(service, file_id)
        if not temp_file_path:
            print(f"Failed to download file: {file_name}")
            return None
        
        # Get OpenAI API key
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            print("Error: OPENAI_API_KEY environment variable not set")
            return None
        
        # Transcribe the audio file
        print(f"Transcribing audio file: {file_name}")
        from audio_transcriber import transcribe_audio
        result = transcribe_audio(openai_api_key, temp_file_path)
        
        if not result["success"]:
            print(f"Error transcribing audio: {result.get('error', 'Unknown error occurred')}")
            return None
        
        transcription = result["transcription"]
        print("Transcription completed successfully.")
        
        # Analyze the transcription
        print(f"Analyzing content from: {file_name}")
        from caption_analyzer import analyze_caption
        analysis_result = analyze_caption(openai_api_key, transcription)
        
        if not analysis_result["success"]:
            print(f"Error analyzing content: {analysis_result.get('error', 'Unknown error occurred')}")
            return None
        
        # Create output data
        output_data = {
            "original_file": file_name,
            "transcription": transcription,
            "analysis": analysis_result["analysis"]
        }
        
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            print(f"Cleaned up temporary file: {temp_file_path}")
        
        return output_data
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return None

def process_folder(folder_id, indent_level=0):
    """Process all audio files in a Google Drive folder and its subfolders."""
    # Get Google Drive service with write access
    service = get_google_drive_service()
    
    # Get folder name
    try:
        folder_metadata = service.files().get(
            fileId=folder_id,
            fields="name",
            supportsAllDrives=True
        ).execute()
        folder_name = folder_metadata.get('name', f"Folder {folder_id}")
    except Exception as e:
        print(f"Error getting folder name: {str(e)}")
        folder_name = f"Folder {folder_id}"
    
    # Create indentation for better readability
    indent = "  " * indent_level
    
    # List all files in the current folder
    all_files = list_files_in_folder(service, folder_id, [])
    
    # Print folder name
    print(f"{indent}[FOLDER] {folder_name} (ID: {folder_id})")
    
    # Get the map of processed files for this folder
    processed_files_map = get_processed_files_map(service, folder_id)
    
    # Separate files and folders
    subfolders = [f for f in all_files if f.get('mimeType') == 'application/vnd.google-apps.folder']
    regular_files = [f for f in all_files if f.get('mimeType') != 'application/vnd.google-apps.folder']
    
    # Print only audio files
    audio_files_in_folder = [f for f in regular_files if any(f['name'].lower().endswith(ext) for ext in AUDIO_EXTENSIONS)]
    if audio_files_in_folder:
        for file in audio_files_in_folder:
            file_name = file['name']
            file_id = file['id']
            print(f"{indent}  [AUDIO] {file_name} (ID: {file_id})")
    
    # Process subfolders recursively without printing their names again
    if subfolders:
        for subfolder in subfolders:
            subfolder_id = subfolder['id']
            # Recursively process the subfolder without printing its name again
            process_folder(subfolder_id, indent_level + 1)
    
    # Process audio files in the current folder
    audio_files = list_files_in_folder(service, folder_id, AUDIO_EXTENSIONS)
    
    if audio_files:
        print(f"{indent}  Processing {len(audio_files)} audio files in folder: {folder_name}")
        
        # Process each audio file
        for file in audio_files:
            file_id = file['id']
            file_name = file['name']
            
            # Get the parent folder ID
            parent_folder_id = get_file_parent_folder(service, file_id)
            if not parent_folder_id:
                print(f"{indent}  Could not determine parent folder for file: {file_name}")
                continue
            
            # Check if this file has already been processed using the cached map
            if check_if_processed_file_exists(processed_files_map, file_name):
                continue
            
            print(f"{indent}  Processing file: {file_name}")
            
            # Process the audio file
            output_data = process_audio_file(service, file_id, file_name)
            if not output_data:
                print(f"{indent}  Failed to process file: {file_name}")
                continue
            
            # Create output filename
            base_name = os.path.splitext(file_name)[0]
            output_filename = f"{base_name}{OUTPUT_FILE_AFFIX}{OUTPUT_FILE_EXTENSION}"
            
            # Save output to a temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=OUTPUT_FILE_EXTENSION) as temp_file:
                json.dump(output_data, temp_file, indent=2)
                temp_file_path = temp_file.name
            
            # Upload the output file to the same folder as the original
            upload_file_to_drive(service, temp_file_path, parent_folder_id, output_filename)
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            print(f"{indent}  Completed processing: {file_name}")
    else:
        print(f"{indent}  No audio files found in folder: {folder_name}")

def extract_folder_id_from_link(link: str) -> str:
    """Extract folder ID from a Google Drive link."""
    # Pattern for Google Drive folder links with user ID
    pattern = r'https://drive\.google\.com/drive/u/\d+/folders/([a-zA-Z0-9_-]+)'
    match = re.search(pattern, link)
    if match:
        return match.group(1)
    
    # Pattern for standard Google Drive folder links
    pattern = r'https://drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)'
    match = re.search(pattern, link)
    if match:
        return match.group(1)
    
    # If the input is already a folder ID (no URL pattern found)
    if re.match(r'^[a-zA-Z0-9_-]+$', link):
        return link
    
    print(f"Error: Could not extract folder ID from link: {link}")
    return None

def main():
    parser = argparse.ArgumentParser(description='Process audio files in a Google Drive folder')
    parser.add_argument('--folder', '-f', required=True, help='ID or link of the Google Drive folder to process')
    args = parser.parse_args()
    
    # Extract folder ID from the provided link or ID
    folder_id = extract_folder_id_from_link(args.folder)
    if not folder_id:
        print("Error: Invalid Google Drive folder link or ID")
        return
    
    # Process the folder
    process_folder(folder_id)

if __name__ == "__main__":
    main() 