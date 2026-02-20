#!/usr/bin/env bash
#
# Deploy Suksham Vachak to Raspberry Pi
#
# Usage:
#   ./scripts/deploy-to-pi.sh                    # Uses default PI_HOST
#   ./scripts/deploy-to-pi.sh pi@192.168.1.100   # Custom host
#   PI_HOST=mypi.local ./scripts/deploy-to-pi.sh # Via environment variable
#
# Prerequisites:
#   - Docker installed locally (with buildx for cross-platform builds)
#   - SSH access to Pi (ssh-copy-id recommended for passwordless)
#   - Docker installed on Pi
#   - lan_proxy network and homelab_sockets volume on Pi
#

set -euo pipefail

# Configuration
PI_HOST="${1:-${PI_HOST:-rpi-pihole}}"
PI_DIR="${PI_DIR:-~/homelab/suksham-vachak}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLATFORM="linux/arm64"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Temporary directory for build artifacts
BUILD_DIR="${PROJECT_ROOT}/.deploy-cache"
mkdir -p "$BUILD_DIR"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Suksham Vachak → Raspberry Pi Deployment"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "  Target:     $PI_HOST"
echo "  Remote dir: $PI_DIR"
echo "  Platform:   $PLATFORM"
echo ""

# Step 1: Build Docker images for ARM64
log_info "Building backend image for $PLATFORM..."
docker build \
    --platform "$PLATFORM" \
    -t suksham-vachak-backend:latest \
    -f "$PROJECT_ROOT/Dockerfile" \
    "$PROJECT_ROOT"
log_success "Backend image built"

log_info "Building frontend image for $PLATFORM (API_URL='' for relative URLs)..."
docker build \
    --platform "$PLATFORM" \
    --build-arg NEXT_PUBLIC_API_URL="" \
    -t suksham-vachak-frontend:latest \
    -f "$PROJECT_ROOT/frontend/Dockerfile" \
    "$PROJECT_ROOT/frontend"
log_success "Frontend image built"

# Step 2: Save images to tar files
log_info "Saving images to tar.gz..."
docker save suksham-vachak-backend:latest | gzip > "$BUILD_DIR/backend.tar.gz"
docker save suksham-vachak-frontend:latest | gzip > "$BUILD_DIR/frontend.tar.gz"

BACKEND_SIZE=$(du -h "$BUILD_DIR/backend.tar.gz" | cut -f1)
FRONTEND_SIZE=$(du -h "$BUILD_DIR/frontend.tar.gz" | cut -f1)
log_success "Images saved: backend ($BACKEND_SIZE), frontend ($FRONTEND_SIZE)"

# Step 3: Create remote directory structure
log_info "Creating remote directory on Pi..."
ssh "$PI_HOST" "mkdir -p $PI_DIR"

# Step 4: Copy files to Pi
log_info "Copying images to Pi (this may take a few minutes)..."
scp "$BUILD_DIR/backend.tar.gz" "$BUILD_DIR/frontend.tar.gz" "$PI_HOST:$PI_DIR/"

log_info "Copying Pi-specific docker-compose.yml..."
scp "$PROJECT_ROOT/deploy/pi/docker-compose.yml" "$PI_HOST:$PI_DIR/"

log_success "Files transferred to Pi"

# Step 5: Load images on Pi
log_info "Loading images on Pi..."
ssh "$PI_HOST" << 'REMOTE_SCRIPT'
cd ~/homelab/suksham-vachak

echo "Loading backend image..."
gunzip -c backend.tar.gz | docker load

echo "Loading frontend image..."
gunzip -c frontend.tar.gz | docker load

echo "Cleaning up tar files..."
rm -f backend.tar.gz frontend.tar.gz

echo "Images loaded:"
docker images | grep -E "(suksham|REPOSITORY)"
REMOTE_SCRIPT

log_success "Images loaded on Pi"

# Step 6: Check for .env file
log_info "Checking for .env file on Pi..."
if ssh "$PI_HOST" "test -f $PI_DIR/.env"; then
    log_success ".env file exists"
else
    log_warn ".env file not found on Pi!"
    echo ""
    echo "  Create it from the example:"
    echo ""
    echo "    ssh $PI_HOST"
    echo "    cd $PI_DIR"
    echo "    cp /path/to/.env.example .env"
    echo "    # Edit .env with your API keys"
    echo ""
fi

# Step 7: Offer to start containers
echo ""
read -p "Start containers on Pi now? [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Starting containers on Pi..."
    ssh "$PI_HOST" "cd $PI_DIR && docker compose up -d"

    echo ""
    log_success "Deployment complete!"
    echo ""
    echo "  The site should be available at:"
    echo "    https://sukshamvachak.com"
    echo ""
    echo "  Useful commands on Pi:"
    echo "    cd $PI_DIR"
    echo "    docker compose logs -f       # View logs"
    echo "    docker compose ps            # Check status"
    echo "    docker compose down          # Stop containers"
    echo "    docker compose up -d         # Start containers"
    echo ""
else
    echo ""
    log_success "Images deployed! To start manually:"
    echo ""
    echo "    ssh $PI_HOST"
    echo "    cd $PI_DIR"
    echo "    docker compose up -d"
    echo ""
fi

# Cleanup local build cache
read -p "Remove local build cache (~${BACKEND_SIZE} + ~${FRONTEND_SIZE})? [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "$BUILD_DIR"
    log_success "Build cache cleaned"
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Deployment finished!"
echo "═══════════════════════════════════════════════════════════"
echo ""
