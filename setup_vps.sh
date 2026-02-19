#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting OSP Server VPS Setup...${NC}"

# 1. Update system
echo -e "${GREEN}Updating system packages...${NC}"
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install Docker & Docker Compose
if ! command -v docker &> /dev/null; then
    echo -e "${GREEN}Installing Docker...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
else
    echo -e "${GREEN}Docker already installed.${NC}"
fi

# 3. Setup Firewall (UFW)
echo -e "${GREEN}Configuring Firewall (UFW)...${NC}"
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp
echo "y" | sudo ufw enable

# 4. Create Project Directory
PROJECT_DIR=~/osp_server
mkdir -p $PROJECT_DIR
echo -e "${GREEN}Project directory created at $PROJECT_DIR${NC}"

# 5. Instructions
echo -e "${GREEN}Setup Complete!${NC}"
echo "------------------------------------------------"
echo "Next steps:"
echo "1. Upload your project files to $PROJECT_DIR"
echo "   (You can use scp or git clone if you have a repo)"
echo "   Example SCP command from your local machine:"
echo "   scp -r 06_Operations/* user@your_vps_ip:$PROJECT_DIR"
echo ""
echo "2. SSH into this server and run:"
echo "   cd $PROJECT_DIR"
echo "   docker compose up -d --build"
echo "------------------------------------------------"
