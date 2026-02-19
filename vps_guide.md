# OSP Server Deployment Guide (VPS)

This guide will help you deploy the OSP Server on a clean Linux server (Ubuntu 20.04/22.04).

## 1. VPS Preparation

You need a server with a public IP address.
**Recommended Providers:**
- **Hetzner Cloud** (CPX11: ~4€/mo) — good price/quality balance.
- **DigitalOcean** (Basic Droplet: ~6$/mo).
- **AWS Lightsail** / **Google Cloud e2-micro**.

**Requirements:**
- OS: Ubuntu 22.04 LTS (recommended)
- CPU: 1-2 vCPU
- RAM: 2GB+ (for Docker and Python)
- Disk: 20GB+

## 2. Server Connection

Open a terminal on your computer:

```bash
# Replace IP_ADDRESS with your server's address
ssh root@IP_ADDRESS
```

## 3. Copying Files

We have prepared all necessary files in the `06_Operations` folder. You need to copy them to the server.
You can do this via `scp` (secure copy) from your local terminal (not on the server, but on your computer):

```bash
# Ensure you are at the project root
cd "/path/to/project"

# Copy folder to server
scp -r 06_Operations root@IP_ADDRESS:~/osp_server_files
```

## 4. Running Setup Script

Return to the SSH session on the server:

```bash
# Go to the folder
cd ~/osp_server_files

# Make script executable
chmod +x setup_vps.sh

# Run automatic setup
./setup_vps.sh
```

**What this script does:**
- Updates system.
- Installs Docker and Docker Compose.
- Configures Firewall (UFW) to open port 8000.

## 5. Starting OSP Server

After successful script execution:

```bash
# Start containers in background mode
docker compose up -d --build

# Check status
docker compose ps

# View logs
docker compose logs -f
```

## 6. Verification

Open in browser or verify via curl:
`http://IP_ADDRESS:8000/docs` — Swagger UI documentation should open.

---

### Optional: Domain Binding (api.amadeq.org)

If you want to use a domain, you need to:
1. Create an `A` record in your DNS panel (Cloudflare):
   - Name: `api`
   - Content: `IP_ADDRESS`
   - Proxy status: DNS Only (initially, to avoid SSL issues) or Proxied (if you configure SSL).

2. For HTTPS (Production), it is recommended to add Nginx as a reverse proxy with Let's Encrypt (Certbot).
