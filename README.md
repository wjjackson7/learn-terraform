# Learn Terraform: Python Web Server on AWS

This project sets up a basic Python web application deployed on an EC2 instance in AWS using Terraform.

## 🧱 Project Structure

```
my-cool-project/
├── app/                   # Python web app (Flask or similar)
│   └── app.py, ...
├── infra/                 # Terraform infrastructure setup
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── setup.sh
│   └── terraform.tfvars
```

## 🚀 Setup Instructions

### 1. Prerequisites

- AWS account with billing enabled
- EC2 key pair named **`terraform`**
- [Install Terraform](https://developer.hashicorp.com/terraform/downloads)
- [Install AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)
- Configure your AWS credentials:

```bash
aws configure
# Enter your AWS Access Key, Secret Key, default region (e.g., us-west-2), and output format
```

### 2. Add Your EC2 Key Pair

Make sure you've created a key pair in the AWS Console named `terraform` (or use CLI):

```bash
aws ec2 create-key-pair --key-name terraform --query 'KeyMaterial' --output text > terraform.pem
chmod 400 terraform.pem
```

### 3. Create a Terraform Variable File

Create `infra/terraform.tfvars` with:

```hcl
key_pair = "terraform"
```

### 4. Initialize and Apply Terraform

```bash
cd infra/
terraform init
terraform apply -auto-approve
```

### 5. Access the Web Server

After apply completes, note the public IP:

```bash
terraform output instance_public_ip
```

Open that IP in your browser — your Python app should be live on port 80.

---

## 🛑 Stop / Destroy the Infrastructure

To shut everything down and avoid charges:

```bash
cd infra/
terraform destroy -auto-approve
```

## 🔍 Debugging Cloud-Init or Setup Script

If your app isn't running as expected, SSH into your instance and check the cloud-init logs:

```bash
ssh -i terraform.pem ubuntu@<public-ip>
```

# Then on the instance:
vi /var/log/cloud-init-output.log

---

## 🧠 Notes

- The EC2 instance runs a basic Flask app using `gunicorn` as defined in `setup.sh`.
- `setup.sh` installs Python 3.9 and sets up your app automatically.
- You can extend this with RDS, Route 53, autoscaling, or Docker.

Happy Terraforming!
