#!/bin/bash
set -e
export TF_VAR_key_pair="your-key-name"
cd infra
terraform init
terraform apply -auto-approve