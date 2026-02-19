
#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}Starting VPS Repair & Setup...${NC}"

# 1. Install Dependencies (Nginx + Certbot)
echo -e "${GREEN}Installing Nginx & Certbot...${NC}"
sudo apt-get update
sudo apt-get install -y nginx certbot python3-certbot-nginx

# 2. Configure Nginx
echo -e "${GREEN}Configuring Nginx...${NC}"
# Remove default if exists
if [ -f /etc/nginx/sites-enabled/default ]; then
    sudo rm /etc/nginx/sites-enabled/default
fi

# Move our config
if [ -f ~/osp_server_files/nginx_osp.conf ]; then
    sudo cp ~/osp_server_files/nginx_osp.conf /etc/nginx/sites-available/osp
    # Link if not exists
    if [ ! -f /etc/nginx/sites-enabled/osp ]; then
        sudo ln -s /etc/nginx/sites-available/osp /etc/nginx/sites-enabled/
    fi
    sudo nginx -t
    sudo systemctl restart nginx
else
    echo "Warning: nginx_osp.conf not found in ~/osp_server_files/"
fi

# 3. Request SSL Certificate (Let's Encrypt)
# Only run if not already set up to avoid rate limits
if [ ! -d "/etc/letsencrypt/live/api.amadeq.org" ]; then
    echo -e "${GREEN}Requesting SSL Certificate for api.amadeq.org...${NC}"
    sudo certbot --nginx -d api.amadeq.org --non-interactive --agree-tos -m admin@amadeq.org
else
    echo -e "${GREEN}SSL Certificate already exists.${NC}"
fi

# 4. Restart Docker Service
echo -e "${GREEN}Restarting OSP Server (Docker)...${NC}"
cd ~/osp_server
# Pull latest if you have an image, or rebuild if you have source
# Assuming source is in ~/osp_server and we rely on docker-compose build
sudo docker compose down
sudo docker compose up -d --build

# 5. Verify
echo -e "${GREEN}Verifying Deployment...${NC}"
sleep 5
curl -I http://localhost:8000/health || echo "Warning: Local health check failed"
curl -I https://api.amadeq.org/health || echo "Warning: Public health check failed"

echo -e "${GREEN}Repair Complete! 🛠️${NC}"
