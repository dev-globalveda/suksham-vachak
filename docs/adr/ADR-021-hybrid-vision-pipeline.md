# ADR-021: Hybrid Vision Pipeline — YOLO26n + Qwen-VL

**Date:** 2026-02-22

**Status:** Accepted

**Deciders:** Aman Misra

## Context

Suksham Vachak needs to "watch" a live cricket broadcast and generate contextual commentary. This requires understanding what's happening on screen — camera angle changes, scorecard updates, shot types, fielding positions, celebrations, etc.

Two model families serve different roles here:

- **YOLO26n** (Ultralytics, Jan 2026): Nano classification model. Runs on Raspberry Pi 5 in ~5ms/frame. Lightweight, real-time, but only outputs a class label (e.g., `pitch_view`). No semantic understanding.
- **Qwen-VL** (Alibaba): Vision-language model. Rich multimodal understanding — can describe scenes, identify actions, read text in context. Too heavy for real-time Pi inference, but available via API or on GPU hardware.

The question: which model drives the vision pipeline, and how do they complement each other?

## Decision

Adopt a **hybrid two-tier architecture** where YOLO26n handles real-time edge inference (Layer 1) and Qwen-VL provides rich scene understanding (Layer 2).

### Layer 1 — YOLO26n (Pi, real-time)

Fast, cheap, always-on. Classifies every frame into one of five scene types:

| Class             | Meaning                                      |
| ----------------- | -------------------------------------------- |
| `pitch_view`      | Live action — batsman, bowler, pitch visible |
| `boundary_view`   | Boundary/outfield camera angle               |
| `replay`          | Slow-motion replay overlay                   |
| `crowd`           | Crowd/stadium/celebration shots              |
| `scorecard_close` | Full-screen scorecard or stats graphic       |

YOLO26n acts as a **trigger/filter** — it tells the system _when_ to engage the heavier layers. No point running OCR or LLM on a crowd shot.

### Layer 1.5 — SSIM + OCR (Pi, on-trigger)

When YOLO26n detects `scorecard_close` or a scene transition:

- **SSIM** (Structural Similarity Index) detects if the scorecard has actually changed
- **EasyOCR** extracts score text from the scorecard region
- Cricket state engine updates match context (runs, wickets, overs)

### Layer 2 — Qwen-VL (API/GPU, on-demand)

When Layer 1 detects a significant event (scene transition, scorecard change, wicket), a key frame is sent to Qwen-VL for rich understanding:

- "Kohli caught at slip, Rabada celebrating"
- "Batsman plays a cover drive, ball racing to the boundary"
- "DRS review in progress, ultra-edge on screen"

This rich description feeds directly into the commentary LLM, producing far more contextual output than class labels alone.

### Layer 3 — Commentary LLM (Claude/Ollama)

Receives structured context from all layers:

```
{
  "scene": "pitch_view",              ← YOLO26n
  "score": "IND 55/5 (9.0 ov)",      ← OCR
  "score_changed": true,              ← SSIM
  "visual_description": "Kohli ...",  ← Qwen-VL
  "persona": "basanti"                ← config
}
```

Generates commentary in the chosen persona's voice and style.

### Data Flow

```
Camera Frame (1 FPS)
  │
  ├──→ YOLO26n (Pi, ~5ms)
  │      └── scene_class: "pitch_view"
  │
  ├──→ SSIM (Pi, ~2ms) [if scorecard region]
  │      └── changed: true/false
  │
  ├──→ OCR (Pi, ~200ms) [if SSIM triggers]
  │      └── score_text: "IND 55/5 (9.0)"
  │
  └──→ Qwen-VL (API, ~2s) [if event detected]
         └── description: "Kohli caught at slip..."
                │
                ▼
         Commentary LLM → TTS → Audio
```

### Qwen-VL as Auto-Labeler

Before the pipeline runs live, Qwen-VL serves a second role: **auto-labeling captured frames** for YOLO26n training. Instead of manually classifying 8,000+ frames via keyboard, we batch-process them through Qwen-VL:

```
Captured Frame → Qwen-VL: "What scene type is this?" → Label → YOLO26n training set
```

This dramatically reduces the manual labeling effort from hours to minutes of review.

## Alternatives Considered

### Qwen-VL Only (no YOLO)

Rich understanding on every frame but too slow (~2s/frame) and expensive for real-time. Would miss fast transitions (wickets happen in one ball). Not viable on Pi hardware.

### YOLO26n Only (no Qwen-VL)

Fast and cheap but commentary limited to "scene changed to pitch view" — no understanding of _what_ is happening. Commentary would depend entirely on OCR score text, missing the visual drama.

### Heavier YOLO Variants (YOLO26s/m)

Better accuracy than nano but still only classification labels. The accuracy gain doesn't justify the compute cost when Qwen-VL provides a qualitatively different capability (understanding vs. labeling).

## Consequences

### Positive

- **Real-time on Pi**: YOLO26n + SSIM + OCR run locally at 1 FPS with headroom
- **Rich commentary**: Qwen-VL provides scene descriptions that make commentary vivid and contextual
- **Cost-efficient**: Qwen-VL only called on events (~5-10% of frames), not every frame
- **Auto-labeling**: Qwen-VL bootstraps the YOLO26n training set, reducing manual effort by 90%+
- **Graceful degradation**: If Qwen-VL API is unavailable, system still functions with YOLO + OCR labels

### Negative

- **API dependency**: Qwen-VL requires network access (or local GPU for self-hosted)
- **Latency**: ~2s delay for Qwen-VL enriched commentary vs. ~200ms for OCR-only
- **Two models to maintain**: YOLO26n training data + Qwen-VL prompt engineering

### Risks

- Qwen-VL may hallucinate cricket details (wrong player names, incorrect shot descriptions)
- YOLO26n trained on G6-camera-pointed-at-TV data may not generalize to clean HDMI capture
- Mitigation: OCR-extracted score serves as ground truth anchor; retrain YOLO on HDMI data when available
