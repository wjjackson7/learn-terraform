import os
import subprocess
import sys
import argparse
import json
import webbrowser
import time

INFRA_DIR = "/Users/wuser/git/learn-terraform/infra"

def package_lambda():
    """Package the Lambda function before deployment."""
    lambda_dir = os.path.join(INFRA_DIR, "lambda")
    package_script = os.path.join(lambda_dir, "package.py")
    
    if not os.path.exists(package_script):
        print("❌ Lambda package script not found")
        sys.exit(1)
        
    print("🔄 Packaging Lambda function...")
    try:
        subprocess.run(
            ["python3", package_script],
            cwd=lambda_dir,
            check=True
        )
        print("✅ Lambda function packaged successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to package Lambda function: {str(e)}")
        sys.exit(1)

def load_config():
    """Load configuration from terraform.tfvars.json"""
    try:
        with open(os.path.join(INFRA_DIR, "terraform.tfvars.json")) as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading terraform.tfvars.json: {str(e)}")
        sys.exit(1)

def run_cmd(cmd, cwd=None):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        sys.exit(1)

def get_instance_id():
    """Get the instance ID from Terraform state if it exists."""
    try:
        result = subprocess.run(
            ["terraform", "output", "-json"],
            cwd=INFRA_DIR,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            outputs = json.loads(result.stdout)
            return outputs.get("instance_id", {}).get("value")
    except Exception:
        pass
    return None

def check_instance_exists():
    """Check if the EC2 instance exists in Terraform state."""
    instance_id = get_instance_id()
    if not instance_id:
        return False
    
    # Check if instance exists in AWS
    try:
        result = subprocess.run(
            ["aws", "ec2", "describe-instances", "--instance-ids", instance_id],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False

def deploy_terraform():
    # Package Lambda function first
    package_lambda()
    
    # Get variables from Terraform
    try:
        result = subprocess.run(
            ["terraform", "output", "-json"],
            cwd=INFRA_DIR,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            outputs = json.loads(result.stdout)
            region = outputs.get("aws_region", {}).get("value", "us-west-2")
            key_pair = outputs.get("key_pair", {}).get("value", "terraform")
        else:
            print("❌ Failed to get Terraform outputs, using defaults")
            region = "us-west-2"
            key_pair = "terraform"
    except Exception as e:
        print(f"❌ Error getting Terraform outputs: {str(e)}")
        region = "us-west-2"
        key_pair = "terraform"
    
    # Check for key pair in the specified region
    try:
        result = subprocess.run(
            ["aws", "ec2", "describe-key-pairs", "--region", region],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            key_pairs = json.loads(result.stdout).get("KeyPairs", [])
            if not any(kp["KeyName"] == key_pair for kp in key_pairs):
                print(f"❌ Key pair '{key_pair}' not found in region {region}")
                sys.exit(1)
            print(f"✅ Found key pair '{key_pair}' in region {region}")
        else:
            print(f"❌ Failed to check key pairs in region {region}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error checking key pairs: {str(e)}")
        sys.exit(1)

    print(f"✅ Using key pair: {key_pair}")

    # Set the region for Terraform
    os.environ["AWS_DEFAULT_REGION"] = region

    # Check if .terraform directory exists
    terraform_dir = os.path.join(INFRA_DIR, ".terraform")
    if os.path.isdir(terraform_dir):
        print("✅ Terraform already initialized.")
    else:
        print("🔄 Initializing Terraform...")
        run_cmd("terraform init", cwd=INFRA_DIR)

    run_cmd("terraform apply -auto-approve -var-file=\"terraform.tfvars.json\"", cwd=INFRA_DIR)

    result = subprocess.run(
        ["terraform", "output", "-raw", "instance_public_ip"],
        cwd=INFRA_DIR, capture_output=True, text=True
    )

    if result.returncode != 0:
        print("❌ Failed to get instance public IP.")
        print(result.stderr)
        sys.exit(1)

    ip = result.stdout.strip()
    try:
        print(f"🔄 Copying credentials to instance at {ip}...")
        cmd = f"scp -i ~/git/learn-terraform/credentials/terraform.pem -r ~/git/learn-terraform/credentials ubuntu@{ip}:~"
        run_cmd(cmd)
    except:
        print("❌ Failed to copy credentials to instance.")

    print(f"✅ Instance public IP: {ip}")

def connect_to_instance():
    result = subprocess.run(
        ["terraform", "output", "-raw", "instance_public_ip"],
        cwd=INFRA_DIR, capture_output=True, text=True
    )

    if result.returncode != 0:
        print("❌ Failed to get instance public IP.")
        print(result.stderr)
        sys.exit(1)

    ip = result.stdout.strip()
    ssh_cmd = f"ssh -i ~/git/learn-terraform/credentials/terraform.pem ubuntu@{ip}"
    print(f"🔗 Connecting to instance at {ip}...")
    os.system(ssh_cmd)

def destroy_infra():
    run_cmd("terraform destroy", cwd=INFRA_DIR)

def stop_instance():
    run_cmd("terraform apply -auto-approve -var='instance_state=stopped'", cwd=INFRA_DIR)

def start_instance():
    run_cmd("terraform apply -auto-approve -var='instance_state=running'", cwd=INFRA_DIR)

def deploy_or_start():
    """Deploy infrastructure if it doesn't exist, otherwise start the instance."""
    if check_instance_exists():
        print("✅ Instance exists, starting it...")
        start_instance()
    else:
        print("🔄 No existing instance found, deploying infrastructure...")
        deploy_terraform()

def load_config():
    """Load configuration from config.json in the infra folder."""
    try:
        with open(os.path.join(INFRA_DIR, "config.json")) as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading config.json: {str(e)}")
        sys.exit(1)

def open_webpage():
    """Open the application's webpage in the default browser."""
    try:
        result = subprocess.run(
            ["terraform", "output", "-raw", "instance_public_ip"],
            cwd=INFRA_DIR,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print("❌ Failed to get instance public IP.")
            print(result.stderr)
            sys.exit(1)

        ip = result.stdout.strip()
        url = f"http://{ip}:8000/docs"
        print(f"🌐 Opening {url} in your default browser...")
        webbrowser.open(url)
    except Exception as e:
        print(f"❌ Error opening webpage: {str(e)}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Manage Terraform EC2 operations.")
    group = parser.add_mutually_exclusive_group()

    group.add_argument("-d", "--deploy", action="store_true", help="Deploy infrastructure or start existing instance")
    group.add_argument("-x", "--destroy", action="store_true", help="Destroy infrastructure")
    group.add_argument("-s", "--stop", action="store_true", help="Stop the EC2 instance")

    parser.add_argument("-c", "--connect", action="store_true", help="SSH into the instance (can be combined with --deploy)")
    parser.add_argument("-w", "--web", action="store_true", help="Open the application's webpage in your default browser")

    args = parser.parse_args()

    if args.deploy:
        deploy_or_start()
    elif args.destroy:
        destroy_infra()
    elif args.stop:
        stop_instance()

    if args.connect:
        connect_to_instance()
    elif args.web:
        open_webpage()
    elif not any([args.deploy, args.destroy, args.stop, args.web]):
        parser.print_help()

if __name__ == "__main__":
    main()