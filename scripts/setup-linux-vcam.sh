#!/usr/bin/env bash
set -euo pipefail
sudo apt-get update
sudo apt-get install -y v4l2loopback-dkms v4l-utils
sudo modprobe v4l2loopback devices=1 exclusive_caps=1 card_label=cam3
echo "OK. Run: python main.py --check"
