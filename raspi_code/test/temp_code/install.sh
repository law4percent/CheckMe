#!/bin/bash

echo "Updating system packages..."
sudo apt-get update

echo "Installing python3-pip..."
sudo apt-get install -y python3-pip

echo "Installing required Python modules with --break-system-packages..."
pip3 install google-generativeai pillow requests RPi.GPIO picamera --break-system-packages

echo "Installation complete!"
