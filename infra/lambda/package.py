import os
import shutil
import subprocess
import sys
from pathlib import Path

def run_command(cmd):
    """Run a shell command and raise an exception if it fails."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Command failed: {cmd}\nError: {result.stderr}")
    return result.stdout

def package_lambda():
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    temp_dir = script_dir / "temp"
    
    try:
        # Create a temporary directory
        print("Creating temporary directory...")
        temp_dir.mkdir(exist_ok=True)
        
        # Install dependencies
        print("Installing dependencies...")
        run_command(f"pip install boto3 -t {temp_dir}")
        
        # Copy the Lambda function
        print("Copying Lambda function...")
        shutil.copy(script_dir / "start_instance.py", temp_dir)
        
        # Create the ZIP file
        print("Creating ZIP file...")
        zip_path = script_dir / "start_instance.zip"
        if zip_path.exists():
            zip_path.unlink()
            
        # Change to temp directory and create zip
        os.chdir(temp_dir)
        run_command(f"zip -r {zip_path} .")
        
        print(f"✅ Successfully created {zip_path}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)
        
    finally:
        # Clean up
        print("Cleaning up...")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    package_lambda() 