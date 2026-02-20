#!/bin/sh
set -e

if [ -n "$UVICORN_UDS" ]; then
    exec python -m uvicorn suksham_vachak.api.app:app --uds "$UVICORN_UDS"
else
    exec python -m uvicorn suksham_vachak.api.app:app --host 0.0.0.0 --port "${UVICORN_PORT:-8000}"
fi
