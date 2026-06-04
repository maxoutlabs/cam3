#!/usr/bin/env bash
# One-time Linux virtual camera setup for cam3 (v4l2loopback).
set -euo pipefail

if ! command -v apt-get >/dev/null 2>&1; then
  echo "This script targets Debian/Ubuntu (apt). See README for other distros."
  exit 1
fi

sudo apt-get update
sudo apt-get install -y v4l2loopback-dkms v4l-utils

sudo modprobe v4l2loopback devices=1 exclusive_caps=1 card_label=cam3

echo ""
echo "Done. Virtual camera should appear as 'cam3' or a Video Loopback device."
echo "Run: python main.py --check"
echo "In Meet/Zoom, select that camera (not your physical webcam)."
