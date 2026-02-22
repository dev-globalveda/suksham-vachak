#!/usr/bin/env bash
#
# Archive completed capture sessions from Pi #2 (aionpi) to Pi #1 (pihole T7 Shield)
#
# Designed to run ON Pi #2 (rpi-aionpi), rsyncing directly to Pi #1 (rpi-pihole).
# Requires SSH certificate access from Pi #2 to Pi #1 (via step-ca).
#
# Usage:
#   ./archive_sessions.sh                            # Archive all sessions
#   ./archive_sessions.sh session_20260222_133707    # Archive specific session
#   DRY_RUN=1 ./archive_sessions.sh                  # Dry run
#   DELETE_SOURCE=1 ./archive_sessions.sh             # Archive + delete source
#
# What it does:
#   1. Rsync raw_frames/ and raw_video/ directly to Pi #1
#   2. Verify file counts match after transfer
#   3. Optionally delete source data on Pi #2 after successful archive
#

set -euo pipefail

# Configuration
DST_HOST="${DST_HOST:-rpi-pihole}"
SRC_BASE="${SRC_BASE:-$HOME/projects/suksham-vision/data}"
DST_BASE="${DST_BASE:-/srv/nfs/datasets/suksham-vision}"
SESSION_FILTER="${1:-}"
DELETE_SOURCE="${DELETE_SOURCE:-0}"
DRY_RUN="${DRY_RUN:-0}"
NOTIFY_TOPIC="${NOTIFY_TOPIC:-suksham-vachak-capture}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

notify() {
    if [ -n "$NOTIFY_TOPIC" ]; then
        curl -s -H "Title: $1" -H "Tags: $2" -d "$3" "https://ntfy.sh/$NOTIFY_TOPIC" > /dev/null 2>&1 || true
    fi
}

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Suksham Vachak — Session Archiver"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "  Source: localhost:${SRC_BASE}"
echo "  Dest:   ${DST_HOST}:${DST_BASE}"
[ -n "$SESSION_FILTER" ] && echo "  Filter: $SESSION_FILTER"
[ "$DRY_RUN" = "1" ] && echo "  Mode:   DRY RUN"
[ "$DELETE_SOURCE" = "1" ] && echo "  Delete: source data after archive"
echo ""

# Verify SSH access to Pi #1
log_info "Checking SSH access to ${DST_HOST}..."
if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "$DST_HOST" "echo ok" > /dev/null 2>&1; then
    log_error "Cannot SSH to ${DST_HOST}. Check your step-ca certificate:"
    echo ""
    echo "    step ssh certificate aionpi@rpi-pihole --provisioner <your-provisioner>"
    echo ""
    exit 1
fi
log_ok "SSH to ${DST_HOST} works"

# Ensure destination directory exists on Pi #1
log_info "Creating archive directory on ${DST_HOST}..."
ssh "$DST_HOST" "mkdir -p ${DST_BASE}/raw_frames ${DST_BASE}/raw_video"

# List sessions to archive
if [ -n "$SESSION_FILTER" ]; then
    SESSIONS="$SESSION_FILTER"
else
    SESSIONS=$(ls -d "${SRC_BASE}/raw_frames/session_"* 2>/dev/null | xargs -n1 basename || true)
fi

if [ -z "$SESSIONS" ]; then
    log_warn "No sessions found to archive."
    exit 0
fi

SESSION_COUNT=$(echo "$SESSIONS" | wc -l | tr -d ' ')
log_info "Found ${SESSION_COUNT} session(s) to archive"
echo ""

TOTAL_FRAMES=0
TOTAL_BYTES=0
TOTAL_ERRORS=0

for SESSION in $SESSIONS; do
    echo "──────────────────────────────────────────"
    log_info "Archiving: ${SESSION}"

    SESSION_DIR="${SRC_BASE}/raw_frames/${SESSION}"
    if [ ! -d "$SESSION_DIR" ]; then
        log_warn "  Session directory not found, skipping"
        continue
    fi

    # Skip sessions with active capture (no session_meta.json = still recording)
    if [ ! -f "${SESSION_DIR}/session_meta.json" ]; then
        log_warn "  Session still active (no session_meta.json), skipping"
        continue
    fi

    # Count source frames
    SRC_FRAME_COUNT=$(ls "${SESSION_DIR}"/frame_*.jpg 2>/dev/null | wc -l | tr -d ' ')
    SRC_SIZE=$(du -sh "$SESSION_DIR" | cut -f1)
    log_info "  Source: ${SRC_FRAME_COUNT} frames (${SRC_SIZE})"

    # Check for A/V file
    VIDEO_FILE="${SRC_BASE}/raw_video/${SESSION}.mkv"
    HAS_VIDEO="no"
    VIDEO_SIZE=""
    if [ -f "$VIDEO_FILE" ]; then
        HAS_VIDEO="yes"
        VIDEO_SIZE=$(du -sh "$VIDEO_FILE" | cut -f1)
        log_info "  A/V file: ${VIDEO_SIZE}"
    fi

    RSYNC_FLAGS="-az --info=progress2"
    [ "$DRY_RUN" = "1" ] && RSYNC_FLAGS="-az --dry-run --stats"

    # Direct rsync: Pi #2 → Pi #1
    log_info "  Syncing frames..."
    rsync $RSYNC_FLAGS \
        -e "ssh" \
        "${SESSION_DIR}/" \
        "${DST_HOST}:${DST_BASE}/raw_frames/${SESSION}/" 2>&1 | tail -3

    # Rsync video if exists
    if [ "$HAS_VIDEO" = "yes" ]; then
        log_info "  Syncing A/V (${VIDEO_SIZE})..."
        rsync $RSYNC_FLAGS \
            -e "ssh" \
            "${VIDEO_FILE}" \
            "${DST_HOST}:${DST_BASE}/raw_video/${SESSION}.mkv" 2>&1 | tail -3
    fi

    # Verify transfer
    if [ "$DRY_RUN" != "1" ]; then
        DST_FRAME_COUNT=$(ssh "$DST_HOST" "ls ${DST_BASE}/raw_frames/${SESSION}/frame_*.jpg 2>/dev/null | wc -l" | tr -d ' ')

        if [ "$SRC_FRAME_COUNT" = "$DST_FRAME_COUNT" ]; then
            log_ok "  Verified: ${DST_FRAME_COUNT}/${SRC_FRAME_COUNT} frames"
            TOTAL_FRAMES=$((TOTAL_FRAMES + DST_FRAME_COUNT))

            # Optionally delete source
            if [ "$DELETE_SOURCE" = "1" ]; then
                log_warn "  Deleting source data..."
                rm -rf "${SESSION_DIR}" "${VIDEO_FILE}" 2>/dev/null
                log_ok "  Source deleted"
            fi
        else
            log_error "  MISMATCH: src=${SRC_FRAME_COUNT} dst=${DST_FRAME_COUNT} — skipping delete"
            TOTAL_ERRORS=$((TOTAL_ERRORS + 1))
        fi
    fi

    echo ""
done

# Summary
echo "═══════════════════════════════════════════════════════════"
if [ "$DRY_RUN" = "1" ]; then
    log_info "Dry run complete. No files transferred."
else
    log_ok "Archive complete: ${TOTAL_FRAMES} frames across ${SESSION_COUNT} session(s)"
    [ "$TOTAL_ERRORS" -gt 0 ] && log_error "Errors: ${TOTAL_ERRORS} session(s) had mismatches"

    # Show disk usage
    echo ""
    log_info "Disk usage:"
    echo "  Pi #2 (local):"
    du -sh "${SRC_BASE}/raw_frames/" "${SRC_BASE}/raw_video/" 2>/dev/null | sed 's/^/    /'
    echo "  Pi #1 (T7 Shield):"
    ssh "$DST_HOST" "du -sh ${DST_BASE}/raw_frames/ ${DST_BASE}/raw_video/ 2>/dev/null" | sed 's/^/    /'

    notify "Archive Complete" "checkered_flag" "Archived ${TOTAL_FRAMES} frames from ${SESSION_COUNT} session(s) to T7 Shield"
fi
echo "═══════════════════════════════════════════════════════════"
echo ""
