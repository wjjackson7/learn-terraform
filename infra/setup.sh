#!/bin/bash
set -e

# Install dependencies
apt update -y
apt install -y software-properties-common

# Add Python 3.9
add-apt-repository ppa:deadsnakes/ppa -y
apt update -y
apt install -y python3.9 python3.9-venv python3.9-distutils curl git

# Install pip for Python 3.9
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.9

# Clone and set up your app
sudo git clone https://github.com/wjjackson7/learn-terraform.git /opt/app
cd /opt/app

# Optional: use virtual environment
sudo python3.9 -m venv venv
source venv/bin/activate

# Install dependencies
sudo pip install -r app/requirements.txt

# Start the app (adjust app:app to your actual entry point)
python3 api.py &
