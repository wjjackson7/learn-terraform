import os
import subprocess
import sys
import argparse

INFRA_DIR = "/Users/wuser/git/learn-terraform/infra"

def run_cmd(cmd, cwd=None):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        sys.exit(1)

def deploy_terraform():
    key_pair = os.environ.get("TF_VAR_key_pair", "")
    if not key_pair:
        print("❌ TF_VAR_key_pair is not set. Please export it first.")
        print("Run:\n  export TF_VAR_key_pair=your-key-name")
        sys.exit(1)

    print(f"✅ Using key pair: {key_pair}")

    if subprocess.run("test -d .terraform && echo \"true\"|| echo \"false\"", capture_output=True).stdout.decode().strip() == "true":
        print("✅ Terraform already initialized.")
    else:
        print("🔄 Initializing Terraform...")
        run_cmd("terraform init", cwd=INFRA_DIR)

    run_cmd("terraform apply -auto-approve", cwd=INFRA_DIR)

    result = subprocess.run(
        ["terraform", "output", "-raw", "instance_public_ip"],
        cwd=INFRA_DIR, capture_output=True, text=True
    )

    if result.returncode != 0:
        print("❌ Failed to get instance public IP.")
        print(result.stderr)
        sys.exit(1)

    ip = result.stdout.strip()
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
    print(f"🔗 o instance at {ip}...")
    os.system(ssh_cmd)

def destroy_infra():
    run_cmd("terraform destroy", cwd=INFRA_DIR)

def stop_instance():
    run_cmd("terraform apply -auto-approve -var='instance_state=stopped'", cwd=INFRA_DIR)

def main():
    parser = argparse.ArgumentParser(description="Manage Terraform EC2 operations.")
    group = parser.add_mutually_exclusive_group()

    group.add_argument("-d", "--deploy", action="store_true", help="Deploy infrastructure")
    group.add_argument("-x", "--destroy", action="store_true", help="Destroy infrastructure")
    group.add_argument("-s", "--stop", action="store_true", help="Stop the EC2 instance")

    parser.add_argument("-c", "--connect", action="store_true", help="SSH into the instance (can be combined with --deploy)")

    args = parser.parse_args()

    if args.deploy:
        deploy_terraform()

    elif args.destroy:
        destroy_infra()

    elif args.stop:
        stop_instance()

    if args.connect:
        connect_to_instance()

    else:
        parser.print_help()

if __name__ == "__main__":
    main()