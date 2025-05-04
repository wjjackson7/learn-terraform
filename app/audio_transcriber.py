import os
import openai
from typing import Dict, Any, Optional
from pydub import AudioSegment
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from dotenv import load_dotenv
import argparse
import shutil

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

#max size before openai rejects request
MAX_CHUNK_SIZE = 25 * 1024 * 1024  # 25MB

def export_chunk(chunk, chunk_path):
    """Export a chunk to MP3."""
    chunk.export(chunk_path, format="mp3")
    return chunk_path

def split_audio(file_path, chunk_dir=None, chunk_length_ms=5 * 60 * 1000, max_threads=4):
    """Split audio into ~5-minute chunks and export them in parallel."""
    # Create a temporary directory if none provided
    if chunk_dir is None:
        chunk_dir = tempfile.mkdtemp(prefix="audio_chunks_")
    
    os.makedirs(chunk_dir, exist_ok=True)
    
    try:
        # Load the audio file
        print(f"Loading audio file: {file_path}")
        audio = AudioSegment.from_file(file_path)
        print(f"Audio duration: {len(audio)/1000/60:.2f} minutes")
        
        # Calculate number of chunks needed
        total_chunks = (len(audio) + chunk_length_ms - 1) // chunk_length_ms
        print(f"Splitting into {total_chunks} chunks of approximately {chunk_length_ms/1000/60:.1f} minutes each")
        
        tasks = []
        # Split up audio into chunks that can be transcribed concurrently
        for i, start in enumerate(range(0, len(audio), chunk_length_ms)):
            end = min(start + chunk_length_ms, len(audio))
            chunk = audio[start:end]
            chunk_path = os.path.join(chunk_dir, f"chunk_{i:04d}.mp3")
            tasks.append((chunk, chunk_path))
        
        chunk_paths = []
        
        # Run the export chunk utilizing threads, also adding a progress bar
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = [executor.submit(export_chunk, chunk, path) for chunk, path in tasks]
            for future in tqdm(as_completed(futures), total=len(futures), desc="Exporting chunks"):
                chunk_paths.append(future.result())
        
        # Verify chunk sizes
        for chunk_path in chunk_paths:
            size = os.path.getsize(chunk_path)
            if size > MAX_CHUNK_SIZE:
                print(f"Warning: {chunk_path} is {size/1024/1024:.2f}MB, which exceeds the 25MB limit.")
                print(f"  This chunk may be rejected by the API. Consider reducing chunk_length_ms.")
        
        return chunk_paths, chunk_dir
    except Exception as e:
        print(f"Error splitting audio: {e}")
        # Clean up the temporary directory if we created it
        if chunk_dir and chunk_dir.startswith(tempfile.gettempdir()):
            shutil.rmtree(chunk_dir, ignore_errors=True)
        raise

def transcribe_chunk(chunk_path, chunk_index, total_chunks):
    """Transcribe a single chunk."""
    with open(chunk_path, "rb") as f:
        try:
            # Don't print here, let the progress bar handle the display
            response = openai.Audio.transcribe(
                model="whisper-1",
                file=f
            )
            return response.text
        except Exception as e:
            print(f"Error transcribing {chunk_path}: {e}")
            return ""

def transcribe_chunks(chunks, max_threads=4):
    """Transcribe chunks in parallel."""
    transcripts = []
    total_chunks = len(chunks)
    
    # Create a progress bar for the overall process
    with tqdm(total=total_chunks, desc="Transcribing chunks", unit="chunk") as pbar:
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            # Submit all tasks with their indices
            futures = {
                executor.submit(transcribe_chunk, chunk, i, total_chunks): i 
                for i, chunk in enumerate(chunks)
            }
            
            # Process results as they complete
            for future in as_completed(futures):
                chunk_index = futures[future]
                try:
                    # Update progress bar with chunk information before processing
                    chunk_name = os.path.basename(chunks[chunk_index])
                    pbar.set_postfix({"chunk": f"{chunk_index+1}/{total_chunks}: {chunk_name}"})
                    
                    transcript = future.result()
                    transcripts.append(transcript)
                    # Update progress bar
                    pbar.update(1)
                except Exception as e:
                    print(f"Error processing chunk {chunk_index+1}: {e}")
                    pbar.update(1)  # Still update progress even if there was an error
    
    return " ".join(transcripts)

def convert_audio(file_path):
    """Convert audio to text, splitting if needed."""
    file_size = os.path.getsize(file_path)
    print(f"File size: {file_size/1024/1024:.2f}MB")
    
    if file_size < MAX_CHUNK_SIZE:
        #print("File is small enough to process directly")
        return transcribe_chunks([file_path])
    else:
        #print(f"File is too large ({file_size/1024/1024:.2f}MB), splitting into chunks")
        chunks, chunk_dir = split_audio(file_path)
        try:
            result = transcribe_chunks(chunks)
            return result
        finally:
            # Clean up the temporary directory if we created it
            if chunk_dir and chunk_dir.startswith(tempfile.gettempdir()):
                shutil.rmtree(chunk_dir, ignore_errors=True)

def transcribe_audio(openai_api_key: str, audio_file_path: str) -> Dict[str, Any]:
    """Transcribe an audio file using OpenAI's Whisper model."""
    try:
        # Initialize OpenAI client
        openai.OpenAI(api_key=openai_api_key)
        
        # Check if the file exists
        if not os.path.exists(audio_file_path):
            return {
                "success": False,
                "error": f"Audio file not found: {audio_file_path}"
            }
        
        # Get file size
        file_size = os.path.getsize(audio_file_path)
        print(f"Processing audio file: {audio_file_path} ({file_size/1024/1024:.2f}MB)")
        
        # Transcribe the audio
        transcription = convert_audio(audio_file_path)
        
        if not transcription:
            return {
                "success": False,
                "error": "Transcription failed or returned empty result"
            }
        
        return {
            "success": True,
            "transcription": transcription
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error transcribing audio: {str(e)}"
        }

def transcribe_audio_from_drive(openai_api_key: str, service, file_id: str) -> Dict[str, Any]:
    """
    Download an audio file from Google Drive and transcribe it.
    
    Args:
        openai_api_key: Your OpenAI API key
        service: Google Drive service
        file_id: ID of the audio file in Google Drive
        
    Returns:
        Dictionary containing the transcription results
    """
    try:
        # Create a temporary file to store the downloaded audio
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Download the file from Google Drive
        request = service.files().get_media(fileId=file_id)
        with open(temp_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        
        # Transcribe the audio file
        result = transcribe_audio(openai_api_key, temp_path)
        
        # Clean up the temporary file
        os.unlink(temp_path)
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Error downloading or transcribing audio from Drive: {str(e)}"
        }

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Transcribe audio files using OpenAI Whisper')
    parser.add_argument('input_path', help='Path to the audio file to transcribe')
    parser.add_argument('--output', '-o', help='Path to save the transcript (default: transcript.txt)')
    args = parser.parse_args()
    
    # Get input and output paths
    input_path = args.input_path
    output_path = args.output if args.output else "transcript.txt"
    
    # Check if input file exists
    if not os.path.exists(input_path):
        print(f"Error: File not found: {input_path}")
        exit(1)
    
    print(f"Transcribing: {input_path}")
    final_text = convert_audio(input_path)
    
    # Save transcript to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_text)
    
    print(f"\nFINAL TRANSCRIPT SAVED TO: {output_path}")
