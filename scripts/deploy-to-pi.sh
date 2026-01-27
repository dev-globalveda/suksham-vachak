#!/usr/bin/env bash
#
# Deploy Suksham Vachak to Raspberry Pi
#
# Usage:
#   ./scripts/deploy-to-pi.sh                    # Uses default PI_HOST=raspberrypi.local
#   ./scripts/deploy-to-pi.sh pi@192.168.1.100   # Custom host
#   PI_HOST=mypi.local ./scripts/deploy-to-pi.sh # Via environment variable
#
# Prerequisites:
#   - Docker installed locally
#   - SSH access to Pi (ssh-copy-id recommended for passwordless)
#   - Docker installed on Pi
#

set -euo pipefail

# Configuration
PI_HOST="${1:-${PI_HOST:-pi@raspberrypi.local}}"
PI_DIR="${PI_DIR:-~/suksham}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
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
echo "  Project:    $PROJECT_ROOT"
echo ""

# Step 1: Build Docker images
log_info "Building Docker images..."
cd "$PROJECT_ROOT"
docker compose build

# Get actual image names from docker compose
BACKEND_IMAGE=$(docker compose images backend --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | head -1)
FRONTEND_IMAGE=$(docker compose images frontend --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | head -1)

# Fallback to common naming patterns if above doesn't work
if [[ -z "$BACKEND_IMAGE" || "$BACKEND_IMAGE" == ":" ]]; then
    BACKEND_IMAGE="suksham-vachak-backend:latest"
fi
if [[ -z "$FRONTEND_IMAGE" || "$FRONTEND_IMAGE" == ":" ]]; then
    FRONTEND_IMAGE="suksham-vachak-frontend:latest"
fi

log_success "Images built: $BACKEND_IMAGE, $FRONTEND_IMAGE"

# Step 2: Save images to tar files
log_info "Saving images to tar.gz (this may take a minute)..."
docker save "$BACKEND_IMAGE" | gzip > "$BUILD_DIR/backend.tar.gz"
docker save "$FRONTEND_IMAGE" | gzip > "$BUILD_DIR/frontend.tar.gz"

BACKEND_SIZE=$(du -h "$BUILD_DIR/backend.tar.gz" | cut -f1)
FRONTEND_SIZE=$(du -h "$BUILD_DIR/frontend.tar.gz" | cut -f1)
log_success "Images saved: backend ($BACKEND_SIZE), frontend ($FRONTEND_SIZE)"

# Step 3: Create remote directory structure
log_info "Creating remote directory structure on Pi..."
ssh "$PI_HOST" "mkdir -p $PI_DIR/data/cricsheet_sample $PI_DIR/credentials"

# Step 4: Copy files to Pi
log_info "Copying files to Pi (this may take a few minutes)..."

# Copy Docker images
scp "$BUILD_DIR/backend.tar.gz" "$BUILD_DIR/frontend.tar.gz" "$PI_HOST:$PI_DIR/"

# Copy docker-compose.yml
scp "$PROJECT_ROOT/docker-compose.yml" "$PI_HOST:$PI_DIR/"

# Copy sample match data
log_info "Copying match data..."
scp -r "$PROJECT_ROOT/data/cricsheet_sample/"* "$PI_HOST:$PI_DIR/data/cricsheet_sample/" 2>/dev/null || true

log_success "Files transferred to Pi"

# Step 5: Load images and start containers on Pi
log_info "Loading images on Pi..."
ssh "$PI_HOST" << 'REMOTE_SCRIPT'
cd ~/suksham

echo "Loading backend image..."
gunzip -c backend.tar.gz | docker load

echo "Loading frontend image..."
gunzip -c frontend.tar.gz | docker load

echo "Cleaning up tar files..."
rm -f backend.tar.gz frontend.tar.gz

echo "Images loaded successfully!"
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
    echo "  Create it with your API keys:"
    echo ""
    echo "    ssh $PI_HOST"
    echo "    cd $PI_DIR"
    echo "    cat > .env << 'EOF'"
    echo "    ANTHROPIC_API_KEY=sk-ant-..."
    echo "    ELEVENLABS_API_KEY=..."
    echo "    EOF"
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
    echo "  Access the app at:"
    echo "    http://${PI_HOST#*@}:3000"
    echo ""
    echo "  Useful commands on Pi:"
    echo "    docker compose logs -f      # View logs"
    echo "    docker compose ps           # Check status"
    echo "    docker compose down         # Stop containers"
    echo "    docker compose up -d        # Start containers"
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

# Cleanup local build cache (optional)
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
