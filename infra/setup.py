#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, check=True):
    """Run a shell command and optionally check its return code."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result.stdout

def get_shell_var(var_name):
    """Get a variable from the shell environment."""
    value = os.environ.get(var_name)
    if value is None:
        raise ValueError(f"Environment variable {var_name} not set")
    return value

def setup_environment():
    """Set up the system environment."""
    print("Updating package lists...")
    run_command("apt update -y")
    
    print("Installing system dependencies...")
    run_command("apt install -y software-properties-common jq")
    
    print("Adding Python 3.9 repository...")
    run_command("add-apt-repository ppa:deadsnakes/ppa -y")
    run_command("apt update -y")
    
    print("Installing Python 3.9 and other dependencies...")
    run_command("apt install -y python3.9 python3.9-venv python3.9-distutils curl git")
    
    print("Installing pip for Python 3.9...")
    run_command("curl -sS https://bootstrap.pypa.io/get-pip.py | python3.9")

def setup_application(app_repo, app_path):
    """Set up the application."""
    if Path(app_path).exists():
        print(f"Directory {app_path} already exists. Deleting...")
        run_command(f"sudo rm -rf {app_path}")

    print(f"Cloning application repository from {app_repo} to {app_path}...")
    run_command(f"sudo git clone {app_repo} {app_path}")

    print("Setting up Python virtual environment...")
    os.chdir(app_path)
    run_command(f"sudo python3.9 -m venv venv")
    
    print("Activating virtual environment and installing dependencies...")
    venv_python = f"{app_path}/venv/bin/python"
    venv_pip = f"{app_path}/venv/bin/pip"
    run_command(f"{venv_pip} install -r app/requirements.txt")
    
    return venv_python

def stop_instance(region):
    """Stop the EC2 instance."""
    print("Getting instance ID...")
    instance_id = run_command("curl -s http://169.254.169.254/latest/meta-data/instance-id")
    
    print(f"Stopping instance {instance_id}...")
    run_command(f"aws ec2 stop-instances --instance-ids {instance_id} --region {region}")

def main():
    try:
        os.environ["AWS_REGION"] = "${aws_region}"
        os.environ["APP_REPO"] = "${app_repo}"
        os.environ["APP_PATH"] = "${app_path}"
        
        print(f"Variables from environment: aws_region={os.environ["AWS_REGION"]}, app_repo={os.environ["APP_REPO"]}, app_path={os.environ["APP_PATH"]}")
        
        # Set up environment
        setup_environment()
        
        # Set up application
        python_path = setup_application(os.environ["APP_REPO"], os.environ["APP_PATH"])
        
        # Run the application
        print("Starting application...")
        run_command(f"{python_path} {os.environ["APP_PATH"]}/app/api.py")
        
        # Stop the instance
        stop_instance(os.environ["AWS_REGION"])
        
    except Exception as e:
        print(f"Error during setup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 