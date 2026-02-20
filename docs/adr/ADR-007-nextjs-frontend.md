# ADR-007: Next.js + Tailwind Over Streamlit

**Date:** 2026-01-03

**Status:** Accepted

**Deciders:** Aman Misra

## Context

The original plan (PROTOTYPE_BUILD_SCRIPT.md) specified Streamlit for the MVP frontend. During implementation, it became clear that Streamlit's rerun-on-interaction model was too limiting for the UI requirements: persona color transitions, audio playback controls, smooth animations, and fine-grained layout control.

## Decision

Replace Streamlit with **Next.js + Tailwind CSS + Framer Motion**. The frontend is a separate application in `frontend/` that communicates with the FastAPI backend via REST API.

### Alternatives Considered

| Option            | Why Rejected                                                              |
| ----------------- | ------------------------------------------------------------------------- |
| Streamlit         | Reruns entire script on interaction; no animation control; limited layout |
| React (CRA/Vite)  | Viable, but Next.js adds SSR and better project structure                 |
| Svelte            | Smaller ecosystem, fewer component libraries                              |
| Plain HTML + HTMX | Insufficient for audio playback and persona transitions                   |

## Consequences

### Positive

- Full control over UI/UX, animations, and audio playback
- Tailwind enables rapid styling without CSS files
- Framer Motion provides smooth persona color transitions
- SSR capability for future SEO/sharing features
- Professional-grade frontend suitable for demos and interviews

### Negative

- Much higher complexity than Streamlit (separate build step, Node.js dependency)
- Two applications to maintain (FastAPI backend + Next.js frontend)
- Steeper learning curve for contributors unfamiliar with React

### Risks

- Frontend may fall behind backend in feature parity during rapid development
- Node.js dependency adds weight to the Pi deployment (though frontend can be pre-built)
