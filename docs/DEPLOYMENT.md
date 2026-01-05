# Suksham Vachak - Deployment Guide

Deploy Suksham Vachak on a Raspberry Pi with Docker and Cloudflare Tunnel.

## Prerequisites

- Raspberry Pi 4 (4GB+ RAM recommended)
- Docker and Docker Compose installed
- Cloudflare account with tunnel configured
- Domain (e.g., `sukshamvachak.com` or subdomain)

## Quick Start

```bash
# Clone the repository
git clone https://github.com/dev-globalveda/suksham-vachak.git
cd suksham-vachak

# Create environment file
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY

# Create GCP service account credentials (see below)
mkdir -p credentials
# Place gcp-service-account.json in credentials/

# Build and run
docker compose up -d --build

# Check status
docker compose ps
docker compose logs -f
```

## Detailed Setup

### 1. Environment Variables

Create `.env` file:

```bash
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

### 2. Google Cloud TTS Credentials

For Docker deployment, you need a service account (not ADC):

1. Go to [GCP Console - Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Select your project (e.g., `Suksham Vachak Demo`)
3. Create Service Account:
   - Name: `suksham-vachak-tts`
   - Role: `Cloud Text-to-Speech API User`
4. Create Key → JSON → Download
5. Save as `credentials/gcp-service-account.json`

### 3. Build and Run

```bash
# Build containers (first time takes ~10min on Pi)
docker compose build

# Start services
docker compose up -d

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Stop services
docker compose down
```

### 4. Verify Deployment

```bash
# Health check
curl http://localhost:8000/api/health

# List matches
curl http://localhost:8000/api/matches

# Access frontend
open http://localhost:3000
```

## Understanding Docker Images

### Where Are Images Stored?

When you run `docker compose build`, images are built and stored **locally** on your machine:

```
Your Pi's Docker Cache (private)
├── suksham-vachak-backend:latest    (~500MB)
└── suksham-vachak-frontend:latest   (~200MB)
```

**These images are NOT pushed anywhere** - they exist only on your Pi.

### Dockerfile vs Image vs Container

| Artifact   | What It Is                     | Where It Lives       |
| ---------- | ------------------------------ | -------------------- |
| Dockerfile | Build instructions (text file) | GitHub (public)      |
| Image      | Built application (binary)     | Local Docker cache   |
| Container  | Running instance of an image   | Local Docker runtime |

### Optional: Push to Registry

If you want pre-built images (faster deploys, CI/CD), you can push to a registry:

**GitHub Container Registry (GHCR):**

```bash
# Login to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Build with registry tag
docker build -t ghcr.io/dev-globalveda/suksham-vachak-backend:latest .
docker build -t ghcr.io/dev-globalveda/suksham-vachak-frontend:latest ./frontend

# Push to registry
docker push ghcr.io/dev-globalveda/suksham-vachak-backend:latest
docker push ghcr.io/dev-globalveda/suksham-vachak-frontend:latest

# On Pi: Pull instead of build
docker pull ghcr.io/dev-globalveda/suksham-vachak-backend:latest
```

**For now:** Just build locally on Pi. Registry is useful for CI/CD or multiple deployments.

---

## Cloudflare Tunnel Configuration

### Option A: Using cloudflared CLI

Add to your existing tunnel config (`~/.cloudflared/config.yml`):

```yaml
tunnel: your-tunnel-id
credentials-file: /home/pi/.cloudflared/your-tunnel-id.json

ingress:
  # Suksham Vachak
  - hostname: sukshamvachak.com
    service: http://localhost:3000
  - hostname: api.sukshamvachak.com
    service: http://localhost:8000

  # Your other services...
  - hostname: blog.globalveda.net
    service: http://localhost:8080

  # Catch-all
  - service: http_status:404
```

Then restart cloudflared:

```bash
sudo systemctl restart cloudflared
```

### Option B: Cloudflare Dashboard

1. Go to [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/)
2. Access → Tunnels → Your Tunnel → Configure
3. Add Public Hostname:
   - Subdomain: `@` (or `www`)
   - Domain: `sukshamvachak.com`
   - Service: `http://localhost:3000`
4. Add another for API (optional):
   - Subdomain: `api`
   - Domain: `sukshamvachak.com`
   - Service: `http://localhost:8000`

### DNS Setup

If using a new domain:

1. Add domain to Cloudflare
2. Update nameservers at your registrar
3. Tunnel will auto-create CNAME records

## Architecture on Pi

```
┌─────────────────────────────────────────────────────┐
│                  Raspberry Pi                        │
│                                                      │
│  ┌──────────────┐    ┌──────────────────────────┐  │
│  │  cloudflared │───→│ suksham-frontend (:3000) │  │
│  │   (tunnel)   │    └──────────────────────────┘  │
│  └──────────────┘                 │                 │
│         │                         ▼                 │
│         │            ┌──────────────────────────┐  │
│         └───────────→│ suksham-backend (:8000)  │  │
│                      └──────────────────────────┘  │
│                                   │                 │
│                                   ▼                 │
│                      ┌──────────────────────────┐  │
│                      │   External APIs          │  │
│                      │   • Anthropic (Claude)   │  │
│                      │   • Google Cloud TTS     │  │
│                      └──────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## Updating

```bash
cd suksham-vachak

# Pull latest code
git pull origin main

# Rebuild and restart
docker compose down
docker compose build --no-cache
docker compose up -d
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker compose logs backend
docker compose logs frontend

# Common issues:
# - Missing .env file
# - Missing credentials/gcp-service-account.json
# - Port already in use
```

### API not accessible

```bash
# Check if backend is healthy
docker compose ps

# Test directly
curl http://localhost:8000/api/health
```

### No audio / TTS failing

```bash
# Check backend logs for TTS errors
docker compose logs backend | grep -i "tts\|audio\|google"

# Verify credentials file exists
ls -la credentials/gcp-service-account.json

# Test TTS API access from container
docker compose exec backend python -c "
from google.cloud import texttospeech
client = texttospeech.TextToSpeechClient()
print('TTS client initialized successfully')
"
```

### Memory issues on Pi

```bash
# Check memory usage
docker stats

# If low on memory, try building one at a time:
docker compose build backend
docker compose build frontend
```

## Resource Usage

Typical usage on Raspberry Pi 4 (4GB):

| Service  | RAM    | CPU (idle) | CPU (active) |
| -------- | ------ | ---------- | ------------ |
| Backend  | ~150MB | 1%         | 10-30%       |
| Frontend | ~100MB | 1%         | 5-15%        |

## Security Notes

1. **Never commit credentials** - `.gitignore` protects `credentials/*.json`
2. **Use Cloudflare Tunnel** - No exposed ports to internet
3. **Non-root containers** - Both services run as `appuser`
4. **Health checks** - Automatic restart on failure
