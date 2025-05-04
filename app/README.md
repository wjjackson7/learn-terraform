# Caption Analysis Tool

This tool analyzes caption files and audio files using OpenAI's Whisper and o3-mini model. It can process files from your local system or from Google Drive.

## Setup

1. Clone this repository
2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up your environment variables:
   - Create a `.env` file in the root directory
   - Add your OpenAI API key:
     ```
     OPENAI_API_KEY=your_openai_api_key_here
     ```
4. Set up Google Drive API access:
   - Create a service account in Google Cloud Console
   - Download the service account key file and save it as `service-account.json` in the root directory
   - Add the following roles to your service account:
     - Storage Object Creator (`roles/storage.objectCreator`)
     - Storage Object Viewer (`roles/storage.objectViewer`)
     - Storage Object Admin (`roles/storage.objectAdmin`)
   - Share the Google Drive folder with the service account email
   - Enable the Google Drive API in your Google Cloud project
5. For audio transcription, install FFmpeg:
   - **macOS**: `brew install ffmpeg`
   - **Ubuntu/Debian**: `sudo apt-get install ffmpeg`
   - **Windows**: Download from [FFmpeg website](https://ffmpeg.org/download.html) and add to PATH

## Usage

### Command Line Interface

#### Process a local file:
```bash
python main.py --file path/to/your/file.txt
```
or
```bash
python main.py -f path/to/your/file.txt
```

#### Process a local audio file:
```bash
python main.py --file path/to/your/audio.mp3
```
or
```bash
python main.py -f path/to/your/audio.m4a
```

#### Process a Google Drive file:
You can use either a file ID or a Google Drive link:
```bash
python main.py --drive-file 1Byf68VMHpuEIwq1xNdD2GdE_kCbrXy6V
```
or
```bash
python main.py -d 'https://drive.google.com/file/d/1Byf68VMHpuEIwq1xNdD2GdE_kCbrXy6V/view?usp=drive_link'
```

### Python API

You can also use the tool programmatically in your Python code:

```python
from main import process_file

# Process a local text file
process_file("path/to/your/file.txt", is_drive_file=False)

# Process a local audio file
process_file("path/to/your/audio.mp3", is_drive_file=False)

# Process a Google Drive file (using file ID)
process_file("1Byf68VMHpuEIwq1xNdD2GdE_kCbrXy6V", is_drive_file=True)
```

## How It Works

1. The script detects the file type (text or audio) based on the file extension
2. For text files:
   - The content is read directly (if local) or downloaded (if from Google Drive)
   - The content is analyzed using OpenAI's GPT-3.5-turbo model
3. For audio files:
   - The audio is transcribed using OpenAI's Whisper model
   - The transcription is then analyzed using OpenAI's GPT-3.5-turbo model
4. The analysis results are displayed in the console

## Supported File Types

### Text Files
- `.txt`

### Audio Files
- `.mp3`, `.wav`, `.m4a`

## Analysis Criteria

The analysis includes:
- Main topics discussed
- Key points and insights
- Notable patterns or themes
- Overall tone and style

## Error Handling

The script includes error handling for:
- Missing API keys
- Invalid file paths or IDs
- Unsupported file types
- Download failures
- Transcription errors
- Analysis errors

## Temporary Files

When processing Google Drive files, the script:
1. Creates a `/tmp` directory if it doesn't exist
2. Downloads the file to this directory
3. Processes the file
4. Cleans up the temporary file after processing

The `/tmp` directory is excluded from version control via `.gitignore`. 