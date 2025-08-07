#!/bin/bash
sudo apt update -y
sudo apt install -y docker.io
sudo systemctl enable docker
sudo systemctl start docker

sudo docker run -d \
  --name n8n \
  -p 5678:5678 \
  -v /home/opc/.n8n:/home/node/.n8n \
  n8nio/n8n
