# Suksham Vachak - AI Cricket Commentary Engine

> **Status**: Working Prototype
> _सूक्ष्म वाचक — "The Subtle Commentator"_

---

## What This Prototype Demonstrates

An end-to-end pipeline that transforms raw ball-by-ball match data into persona-driven audio commentary:

```
Cricsheet JSON → Context Engine → LLM Generation → TTS Audio
                     ↓
        (Pressure, Momentum, Narrative, Milestones)
                     ↓
        Persona-enforced word limits + style constraints
```

**Live capabilities:**

- **3 distinct personas** with enforced stylistic constraints (word limits, tone, vocabulary)
- **Bilingual output** — English and Hindi, with Hindi as transcreation rather than translation
- **TOON serialization** — custom Token-Oriented Object Notation for ~50% LLM token savings
- **17,020 real Cricsheet matches** as data source (ball-by-ball JSON)
- **ElevenLabs TTS** with persona-mapped voices
- **Auto LLM detection** — Ollama (local) with Claude API fallback
- **Template fallback** — works offline when no LLM is available
- **Rich context** — pressure levels, momentum shifts, batter milestones, narrative tension

---

## The Problem

**"Singular Commentary Torture"**: 1 billion+ cricket viewers forced to hear one commentator, in one language, in one style. 22 official Indian languages, 600M+ regional language speakers — broadcasting serves 2-3 of them. The commentary voice is imposed, never chosen.

This prototype demonstrates the alternative: the same ball, described by different voices, in different languages, with personality preserved across the switch.

---

## Personas (What's Live)

### Richie Benaud — Minimalist Master

- **Word limits**: 1-3 words for wickets and sixes, silence for dot balls
- **Minimalism score**: 0.95 (enforced by both LLM prompt and client-side truncation)
- **Signature**: "Gone." / "Magnificent." / "Four."
- **Voice**: Deep, measured, deliberate

### Tony Greig — Theatrical Showman

- **Word limits**: 5-20 words per event
- **Minimalism score**: 0.2 (verbose, dramatic, every ball is theatre)
- **Signature**: "That's gone into the stands!" / "Absolutely brilliant!"
- **Voice**: Energetic, higher pitch, variable pace

### Sushil Doshi — Hindi Passion

- **Word limits**: Expressive but punchy (minimalism 0.6)
- **Language**: Hindi natively — not translated English
- **Signature**: "आउट! और गया!" / "छक्का! क्या मारा है!"
- **Voice**: Gravitas, slower pace, emotional depth

**The key innovation**: word-limit enforcement happens at two levels — the LLM prompt specifies per-event word budgets, and the engine truncates any output that exceeds them. Benaud's "Gone." stays "Gone." regardless of LLM verbosity.

---

## Technical Architecture (MVP)

### Stack

| Layer    | Technology                                             |
| -------- | ------------------------------------------------------ |
| Backend  | FastAPI + Uvicorn                                      |
| LLM      | Claude API (quality) / Ollama local (cost-free)        |
| TTS      | ElevenLabs (multilingual v2 model)                     |
| Frontend | Next.js + Tailwind + Framer Motion                     |
| Data     | Cricsheet ball-by-ball JSON (17,020 matches available) |

### TOON Serialization

Token-Oriented Object Notation compresses rich match context before sending to the LLM:

```
M
  teams [2] India, Australia
  score 145/3
  overs 23.4
  phase middle
  CRR 6.18
B
  name V Kohli
  runs 52
  balls 45
  SR 115.6
  milestone approaching_fifty
W
  name M Starc
  overs 5.2
  wkts 2
  econ 7.84
P
  level high
  score 0.78
N
  story partnership_building
  tension 0.65
  momentum batting
```

Short keys (M/B/W/P/N), no quotes, array length prefixes — the LLM receives the same context in roughly half the tokens.

### LLM Provider Auto-Detection

1. Check if Ollama is running locally (free, fast, no API key needed)
2. If not, check for `ANTHROPIC_API_KEY` and use Claude
3. If neither available, fall back to template-based generation (no LLM required)

### Context Engine

The `ContextBuilder` processes every ball sequentially to maintain:

- **Match situation**: innings phase, run rate, target/required rate
- **Batter context**: runs, strike rate, approaching milestones
- **Bowler context**: overs, economy, hat-trick tracking
- **Pressure model**: composite score from match state
- **Narrative state**: current storyline, tension level, momentum direction

---

## Demo Flow

1. **Select a curated match** — India vs Pakistan T20 WC 2016, India vs Australia, India vs England
2. **Browse key moments** — wickets, sixes, and fours extracted automatically
3. **Choose persona and generate** — Benaud, Greig, or Doshi; commentary appears with audio
4. **Switch persona** — same ball, different voice, different word count
5. **Switch to Hindi** — same ball, cultural transcreation (not translation)

The UI adapts its color palette to the selected persona and caches generated commentary for instant persona/language switching.

---

## Technology Radar

**Qwen3-TTS** — An open-weight model offering text-to-speech with emotional control. Under consideration as a local, free alternative to ElevenLabs for development and self-hosted deployment.

**Fine-tuning pipeline** — A documented workflow exists (`docs/`) for curating persona training data from the commentary engine's output, evaluating with automated metrics, and fine-tuning smaller models (Qwen/Llama via LoRA) to replace API calls.

---

## Future Horizons

These are defined but not in the current prototype:

- **More personas** — Osho (mystic), Harsha Bhogle (analytical), Feynman (physicist), others defined conceptually
- **More languages** — transcreation approach applies to Tamil, Bengali, Telugu, and beyond
- **Accessibility modes** — deaf (visual+haptic), blind (spatial audio), cognitive (simplified language)
- **Real-time live match integration** — currently post-match replay only
- **Voice cloning** — using reference audio for more authentic persona voices
- **Fine-tuned persona models** — LoRA adapters on open-weight LLMs for cost-free inference

---

## What's NOT in the Prototype

Honesty section — what this prototype does _not_ do:

- **Voice cloning** — uses stock ElevenLabs pre-made voices, not cloned from real commentators
- **Real-time streaming** — generates commentary on demand for recorded matches
- **Accessibility modes** — no deaf/blind/cognitive adaptations implemented
- **100+ languages** — English and Hindi only
- **Style sliders** — personas are discrete choices, not continuously adjustable
- **Revenue model** — no commercial infrastructure

---

## The Transcreation Principle

> Not translation. Transcreation.

**The Benaud Test**: if the translation is longer than the original, it fails.

```
Input: "Gone." (English, Benaud style)

WRONG (translation):
  Hindi: "वह आउट हो गया है।" (6 words - FAILED)

RIGHT (transcreation):
  Hindi: "गया।" (1 word - PASSED)
```

Doshi's Hindi is not Greig translated — it's Hindi cricket passion in its own idiom. "छक्का! क्या मारा है!" is not "Six! What a hit!" mapped word-by-word. It's what a Hindi commentator would actually say.

---

## Origin

Started on New Year's Eve 2025, exploring Cricsheet data in a Jupyter notebook. The question: _"What if Richie Benaud commentated in Hindi — and it still sounded like Benaud?"_

That question became this prototype.
