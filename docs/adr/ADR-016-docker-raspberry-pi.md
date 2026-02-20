# ADR-016: Docker Deployment Targeting Raspberry Pi 5

**Date:** 2026-01-05

**Status:** Accepted

**Deciders:** Aman Misra

## Context

The system's core value proposition is $0.40/match AI commentary vs $500/match human commentators. This requires edge deployment on inexpensive hardware. The deployment must be reproducible, isolated, and manageable by non-experts.

## Decision

- **Raspberry Pi 5 (8-16GB)** as the target edge hardware ($80 device)
- **Docker + Docker Compose** for deployment (multi-stage build, non-root user, health checks)
- **SSH-based deployment script** (`scripts/deploy-to-pi.sh`): builds images locally, exports as tar.gz, SCPs to Pi, loads and starts there
- **Cloudflare Tunnel** for internet access (zero exposed ports, free DDoS protection)
- **Ollama** for local LLM inference on Pi (Qwen2.5 7B Q4_K_M, ~5GB RAM, 6-8 tok/s)

### Alternatives Considered

| Option                        | Why Rejected                                                    |
| ----------------------------- | --------------------------------------------------------------- |
| Cloud-only deployment         | Per-match cost defeats the value proposition                    |
| Jetson Nano                   | More expensive, NVIDIA-specific, harder to source               |
| Intel NUC                     | $300+ — doesn't hit the "$80 device" talking point              |
| Direct Python install on Pi   | No isolation, dependency conflicts, hard to reproduce           |
| Container registry pull on Pi | Pi's bandwidth may be limited; local build+SCP is more reliable |
| CI/CD pipeline for Pi         | Overengineered for a single-device deployment                   |

## Consequences

### Positive

- $80 hardware cost makes the system accessible to small cricket organizations
- Docker provides reproducible deployment regardless of Pi OS version
- Non-root container user, health checks, and restart policies for production safety
- Cloudflare Tunnel eliminates port forwarding and firewall configuration
- Build-local-SCP approach avoids slow ARM cross-compilation on Pi

### Negative

- Docker on Pi consumes ~250MB RAM for both containers (backend + frontend)
- Pi 5 requires active cooling for sustained LLM inference
- NVMe recommended over SD card (adds ~$30 to BOM)
- Deployment script is manual (no GitOps/CI for the Pi target)

### Risks

- Pi 5 supply chain constraints could delay hardware procurement
- 8GB Pi may be insufficient if model sizes grow
- Docker + Ollama + FastAPI on Pi leaves only ~2-3GB for OS and buffers
