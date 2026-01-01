# Suksham Vachak - System Architecture

> **Document Version**: 1.0
> **Last Updated**: January 1, 2026
> **Status**: Approved for MVP Development

---

## Executive Summary

This document defines the technical architecture for Suksham Vachak, a personalized AI commentary platform. We adopt a **phased approach** that allows us to prove our core value proposition (personalized commentary) before tackling the harder problem of live video understanding.

**Key Insight**: Cricsheet JSON data IS the output of a vision-to-events pipeline. By starting with this data, we skip the hardest problem and focus on what makes us unique.

---

## Architecture Overview

### The Full Vision (End State)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SUKSHAM VACHAK - FULL SYSTEM                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────┐    ┌──────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │  Video  │───→│ Vision Model │───→│ Event Extractor │───→│   Unified   │ │
│  │  Feed   │    │  (YOLO/CSP)  │    │   (Custom ML)   │    │   Event     │ │
│  └─────────┘    └──────────────┘    └─────────────────┘    │   Schema    │ │
│                                                             │             │ │
│  ┌─────────┐                                                │   (JSON)   │ │
│  │Cricsheet│───────────────────────────────────────────────→│             │ │
│  │  JSON   │                                                └──────┬──────┘ │
│  └─────────┘                                                       │        │
│                                                                    ▼        │
│                                              ┌─────────────────────────────┐│
│                                              │     COMMENTARY ENGINE       ││
│                                              │  ┌───────────────────────┐  ││
│                                              │  │    Persona Layer      │  ││
│                                              │  │  ┌─────┐ ┌─────┐     │  ││
│                                              │  │  │Benaud│ │Doshi│ ... │  ││
│                                              │  │  └─────┘ └─────┘     │  ││
│                                              │  └───────────────────────┘  ││
│                                              │  ┌───────────────────────┐  ││
│                                              │  │   Language Engine     │  ││
│                                              │  │  EN│HI│TA│TE│BN│...  │  ││
│                                              │  └───────────────────────┘  ││
│                                              │  ┌───────────────────────┐  ││
│                                              │  │      LLM Layer        │  ││
│                                              │  │   (Claude/GPT/etc)    │  ││
│                                              │  └───────────────────────┘  ││
│                                              └──────────────┬──────────────┘│
│                                                             │               │
│                                                             ▼               │
│                                              ┌─────────────────────────────┐│
│                                              │       TTS ENGINE            ││
│                                              │  ┌───────────────────────┐  ││
│                                              │  │   Voice Selection     │  ││
│                                              │  │  (Match to Persona)   │  ││
│                                              │  └───────────────────────┘  ││
│                                              │  ┌───────────────────────┐  ││
│                                              │  │   Prosody Control     │  ││
│                                              │  │  (Emotion, Pace)      │  ││
│                                              │  └───────────────────────┘  ││
│                                              │  ┌───────────────────────┐  ││
│                                              │  │   Audio Generation    │  ││
│                                              │  │  (Google/Azure TTS)   │  ││
│                                              │  └───────────────────────┘  ││
│                                              └──────────────┬──────────────┘│
│                                                             │               │
│                                                             ▼               │
│                                              ┌─────────────────────────────┐│
│                                              │      OUTPUT LAYER           ││
│                                              │  • Audio Stream             ││
│                                              │  • Subtitles                ││
│                                              │  • Haptic (Accessibility)   ││
│                                              └─────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phased Development Approach

### Phase 1: MVP (Weeks 1-4)
**Goal**: Prove personalized commentary works with existing data

```
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 1: MVP ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Cricsheet ───→ Cricket ───→ Commentary ───→ TTS ───→ Audio   │
│     JSON         Parser        Engine                           │
│                                   │                             │
│                            ┌──────┴──────┐                      │
│                            │   PERSONAS  │                      │
│                            │  • Benaud   │                      │
│                            │  • Doshi    │                      │
│                            │  • Osho     │                      │
│                            │  • Greig    │                      │
│                            └─────────────┘                      │
│                                                                 │
│   [WE HAVE]      [BUILD]       [BUILD]      [BUY]    [OUTPUT]  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 2: Enhanced (Months 2-3)
**Goal**: Multi-language support, more personas, production-ready

- Add Hindi, Tamil, Telugu, Bengali TTS
- Expand to 10+ personas
- Build proper web UI
- Add accessibility modes

### Phase 3: Live Video (Months 4+)
**Goal**: Real-time video to commentary (Research Phase)

```
┌─────────────────────────────────────────────────────────────────┐
│                 PHASE 3: LIVE ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Video ───→ Vision ───→ Event ───→ [Same Commentary Engine]   │
│   Stream     Model       Extractor                              │
│     │          │            │                                   │
│  (YouTube)  (YOLO)    (Custom ML)                               │
│              (Azure)   (Fine-tuned                              │
│              (Google)   LLM)                                    │
│                            │                                    │
│                     ┌──────┴──────┐                             │
│                     │ CHALLENGES  │                             │
│                     │ • Player ID │                             │
│                     │ • Shot type │                             │
│                     │ • Score     │                             │
│                     │ • Context   │                             │
│                     └─────────────┘                             │
│                                                                 │
│                  🔬 DEEP RESEARCH REQUIRED 🔬                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Specifications

### 1. Cricket Parser (P0 - MVP)

**Purpose**: Transform Cricsheet JSON into standardized event objects

**Input**: Raw Cricsheet JSON
```json
{
  "innings": [{
    "overs": [{
      "over": 0,
      "deliveries": [{
        "batter": "Rohit Sharma",
        "bowler": "Shaheen Afridi",
        "runs": {"batter": 4, "total": 4},
        ...
      }]
    }]
  }]
}
```

**Output**: CricketEvent objects
```python
@dataclass
class CricketEvent:
    event_type: str          # "BOUNDARY_FOUR", "WICKET", "DOT_BALL"
    batter: str
    bowler: str
    runs: int
    is_boundary: bool
    is_wicket: bool
    wicket_type: Optional[str]
    match_context: MatchContext
    timestamp: float
```

**Complexity**: Low
**Estimated Time**: 1 day

---

### 2. Commentary Engine (P0 - MVP)

**Purpose**: Generate contextual commentary text from cricket events

**Components**:
- **Context Builder**: Builds narrative context (match situation, pressure, momentum)
- **LLM Interface**: Sends prompts to Claude/GPT
- **Response Parser**: Extracts and validates commentary

**Input**: CricketEvent + Persona + Language
**Output**: Commentary text

```python
class CommentaryEngine:
    def generate(
        self,
        event: CricketEvent,
        persona: Persona,
        language: str = "en"
    ) -> str:
        """Generate commentary for a cricket event."""
        prompt = self._build_prompt(event, persona, language)
        response = self.llm.complete(prompt)
        return self._parse_response(response)
```

**Complexity**: Medium
**Estimated Time**: 2-3 days

---

### 3. Persona Layer (P0 - MVP)

**Purpose**: Inject personality, style, and cultural nuance into commentary

**Persona Definition**:
```python
@dataclass
class Persona:
    name: str                    # "Richie Benaud"
    style: str                   # "minimalist"
    vocabulary: List[str]        # Signature phrases
    cultural_context: str        # Australian cricket wisdom
    emotion_range: Dict[str, str]  # How they express emotions
    signature_phrases: List[str]  # "Marvelous!", "Gone."

    # The Benaud Test
    minimalism_score: float      # 0.0 = verbose, 1.0 = "Gone."
```

**MVP Personas**:
| Persona          | Style                 | Language | Minimalism |
| ---------------- | --------------------- | -------- | ---------- |
| Richie Benaud    | Minimalist, Elegant   | EN       | 0.95       |
| Harsha Bhogle    | Analytical, Warm      | EN/HI    | 0.3        |
| Sanjay Manjrekar | Technical, Critical   | EN       | 0.4        |
| Tony Greig       | Exuberant, Dramatic   | EN       | 0.2        |
| Osho             | Mystic, Philosophical | EN/HI    | 0.7        |

**Complexity**: Medium
**Estimated Time**: 1-2 days

---

### 4. TTS Engine (P1 - MVP)

**Purpose**: Convert commentary text to natural speech

**Providers**:
- **Primary**: Google Cloud TTS (WaveNet voices)
- **Fallback**: Azure Cognitive Services
- **Future**: ElevenLabs (voice cloning)

**Features**:
- Voice selection per persona
- Prosody control (pace, pitch, emphasis)
- SSML support for fine-grained control
- Multi-language support

```python
class TTSEngine:
    def synthesize(
        self,
        text: str,
        persona: Persona,
        language: str,
        emotion: str = "neutral"
    ) -> bytes:
        """Generate speech audio from text."""
        ssml = self._apply_prosody(text, persona, emotion)
        return self.provider.synthesize(ssml, voice=persona.voice_id)
```

**Complexity**: Low
**Estimated Time**: 1 day

---

### 5. Language Engine (P2 - Enhanced)

**Purpose**: Generate culturally-appropriate commentary in multiple languages

**Supported Languages (MVP)**:
- English (EN)
- Hindi (HI)
- Tamil (TA)

**Approach**:
1. Generate in target language directly (preferred)
2. Fallback: Generate in English, then translate with cultural adaptation

**The Benaud Test for Hindi**:
```
English: "Gone."
Hindi:   "गया।" (NOT "वह खिलाड़ी अब आउट हो गया है।")
```

**Complexity**: Medium
**Estimated Time**: 2-3 days

---

### 6. Vision-to-Events Pipeline (P3 - Research)

**Purpose**: Extract cricket events from live video

**This is the hardest problem. Challenges include**:

| Challenge                | Difficulty | Notes                                              |
| ------------------------ | ---------- | -------------------------------------------------- |
| Player identification    | Very Hard  | Requires face recognition, jersey numbers, context |
| Shot type classification | Hard       | Pull vs hook, cover drive vs square drive          |
| Ball tracking            | Medium     | Hawk-Eye does this well                            |
| Score extraction         | Easy       | OCR from broadcast graphics                        |
| Context building         | Hard       | Requires understanding game state                  |

**Potential Approaches**:
1. **YOLO + Custom Classifier**: Detect objects, classify events
2. **Azure/Google Vision**: Pre-built object detection
3. **Fine-tuned LLM**: Vision-language models (GPT-4V, Claude Vision)
4. **Hybrid**: OCR for score + Vision for action

**Status**: Research phase. Not in MVP scope.

---

## Data Flow

### MVP Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Cricsheet  │     │   Cricket   │     │   Event     │
│    JSON     │────→│   Parser    │────→│   Queue     │
│             │     │             │     │             │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌──────────────────────────┘
                    ▼
┌─────────────────────────────────────────────────────┐
│                  Commentary Engine                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │   Context   │  │   Persona   │  │     LLM     │  │
│  │   Builder   │─→│   Applier   │─→│  Interface  │  │
│  └─────────────┘  └─────────────┘  └──────┬──────┘  │
└───────────────────────────────────────────┼─────────┘
                                            │
                    ┌───────────────────────┘
                    ▼
┌─────────────────────────────────────────────────────┐
│                    TTS Engine                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │    SSML     │  │   Prosody   │  │   Audio     │  │
│  │  Generator  │─→│   Control   │─→│  Synthesis  │  │
│  └─────────────┘  └─────────────┘  └──────┬──────┘  │
└───────────────────────────────────────────┼─────────┘
                                            │
                    ┌───────────────────────┘
                    ▼
              ┌───────────┐
              │   Audio   │
              │   Output  │
              └───────────┘
```

---

## Technology Stack

### MVP Stack

| Layer           | Technology             | Rationale                        |
| --------------- | ---------------------- | -------------------------------- |
| Language        | Python 3.11+           | Rich ecosystem, fast prototyping |
| Package Manager | Poetry                 | Dependency isolation             |
| LLM             | Claude API (Anthropic) | Best for nuanced text            |
| TTS             | Google Cloud TTS       | WaveNet quality, multi-language  |
| UI              | Streamlit              | Rapid prototyping                |
| API             | FastAPI                | If needed for decoupling         |
| Data            | JSON files             | Simple, no DB needed for MVP     |

### Production Stack (Future)

| Layer         | Technology            | Rationale              |
| ------------- | --------------------- | ---------------------- |
| Backend       | FastAPI + async       | High concurrency       |
| Database      | PostgreSQL            | Structured data        |
| Cache         | Redis                 | Session, audio caching |
| Queue         | RabbitMQ/Redis        | Event processing       |
| Storage       | S3/GCS                | Audio files            |
| CDN           | CloudFront/CloudFlare | Audio delivery         |
| Orchestration | Kubernetes            | Scaling                |

---

## API Contracts

### Internal Event Schema

```python
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum

class EventType(Enum):
    DOT_BALL = "dot_ball"
    SINGLE = "single"
    DOUBLE = "double"
    TRIPLE = "triple"
    BOUNDARY_FOUR = "boundary_four"
    BOUNDARY_SIX = "boundary_six"
    WICKET = "wicket"
    WIDE = "wide"
    NO_BALL = "no_ball"
    BYE = "bye"
    LEG_BYE = "leg_bye"

@dataclass
class MatchContext:
    match_id: str
    teams: tuple[str, str]
    venue: str
    date: str
    format: str  # "T20", "ODI", "Test"
    innings: int
    current_score: int
    current_wickets: int
    overs_completed: float
    target: Optional[int]  # For chasing team
    required_rate: Optional[float]
    current_rate: float

@dataclass
class CricketEvent:
    event_id: str
    event_type: EventType
    ball_number: str  # "15.3" = over 15, ball 3
    batter: str
    bowler: str
    non_striker: str
    runs_batter: int
    runs_extras: int
    runs_total: int
    is_boundary: bool
    is_wicket: bool
    wicket_type: Optional[str]
    wicket_player: Optional[str]
    fielder: Optional[str]
    match_context: MatchContext

    # Future: from vision
    shot_type: Optional[str]  # "cover_drive", "pull", "sweep"
    ball_speed: Optional[float]
    ball_trajectory: Optional[str]
```

### Commentary Request/Response

```python
@dataclass
class CommentaryRequest:
    event: CricketEvent
    persona_id: str
    language: str
    include_audio: bool = True
    audio_format: str = "mp3"

@dataclass
class CommentaryResponse:
    text: str
    audio_url: Optional[str]
    audio_bytes: Optional[bytes]
    duration_seconds: float
    persona_used: str
    language: str
```

---

## Directory Structure

```
suksham-vachak/
├── src/
│   ├── __init__.py
│   ├── parser/
│   │   ├── __init__.py
│   │   ├── cricsheet.py       # Cricsheet JSON parser
│   │   └── events.py          # Event dataclasses
│   ├── commentary/
│   │   ├── __init__.py
│   │   ├── engine.py          # Main commentary engine
│   │   ├── context.py         # Context builder
│   │   └── prompts.py         # LLM prompts
│   ├── personas/
│   │   ├── __init__.py
│   │   ├── base.py            # Persona dataclass
│   │   ├── benaud.py          # Richie Benaud
│   │   ├── doshi.py           # Sushil Doshi
│   │   ├── osho.py            # Osho (mystic)
│   │   └── registry.py        # Persona registry
│   ├── tts/
│   │   ├── __init__.py
│   │   ├── engine.py          # TTS abstraction
│   │   ├── google.py          # Google TTS
│   │   └── azure.py           # Azure TTS
│   ├── languages/
│   │   ├── __init__.py
│   │   ├── engine.py          # Language handling
│   │   └── hindi.py           # Hindi specific
│   └── ui/
│       ├── __init__.py
│       └── streamlit_app.py   # Demo UI
├── data/
│   ├── cricsheet_sample/      # 20 sample matches
│   └── README.md              # Download instructions
├── tests/
│   ├── test_parser.py
│   ├── test_commentary.py
│   └── test_tts.py
├── docs/
│   ├── VISION.md
│   ├── ARCHITECTURE.md        # This file
│   └── PROTOTYPE_BUILD_SCRIPT.md
├── notebooks/
│   └── cricket_data_exploration.ipynb
├── pyproject.toml
├── README.md
└── .env.example
```

---

## Development Priorities

### P0 - Must Have for MVP Demo
- [ ] Cricket Parser (Cricsheet → Events)
- [ ] Commentary Engine (Events → Text)
- [ ] Persona Layer (3 personas: Benaud, Doshi, Osho)
- [ ] TTS Integration (Google TTS)
- [ ] Streamlit Demo UI

### P1 - Should Have
- [ ] Hindi language support
- [ ] Audio caching
- [ ] More personas (Greig, Bhogle, Manjrekar)

### P2 - Nice to Have
- [ ] Tamil language support
- [ ] Pre-generated commentary library
- [ ] Accessibility modes

### P3 - Future Research
- [ ] Vision model integration
- [ ] Live video processing
- [ ] Real-time commentary

---

## Claude CLI Development Prompts

Use these prompts when building with Claude CLI on Mac:

### Starting the Session
```
/plan Let's build Suksham Vachak MVP. I have the architecture in docs/ARCHITECTURE.md.
Let's start with the Cricket Parser component. Review the architecture and confirm
you understand the CricketEvent schema.
```

### Building Components
```
/build Create src/parser/events.py with the CricketEvent and MatchContext dataclasses
as specified in docs/ARCHITECTURE.md
```

```
/build Create src/parser/cricsheet.py that parses Cricsheet JSON files into
CricketEvent objects. Use data/cricsheet_sample/ for testing.
```

```
/build Create src/personas/benaud.py implementing the Richie Benaud persona.
Remember the minimalism test: "Gone." not "The batsman has been dismissed."
```

### Testing
```
/run python -m pytest tests/test_parser.py -v
```

### Integration
```
/edit Wire up the full pipeline: parser → commentary → TTS.
Create a simple demo script that takes a match file and generates
audio commentary for the first over.
```

---

## Success Criteria

### MVP Demo (End of Week 2)
- [ ] Load any Cricsheet match JSON
- [ ] Generate Benaud-style commentary for key moments
- [ ] Output audio in English
- [ ] Demo runs in Streamlit

### Enhanced Demo (End of Month 1)
- [ ] 5+ personas working
- [ ] Hindi + English working
- [ ] Pre-generated audio for sample matches
- [ ] Shareable demo link

### Production Ready (End of Quarter 1)
- [ ] 10+ personas
- [ ] 5+ languages
- [ ] API for third-party integration
- [ ] Mobile-responsive UI

---

## Appendix: The Benaud Test

Every persona and language implementation must pass the Benaud Test:

**The Test**: Can the system produce minimal, elegant commentary?

| Scenario     | ❌ Fail                                                                                   | ✅ Pass         |
| ------------ | ---------------------------------------------------------------------------------------- | -------------- |
| Wicket       | "The batsman has been clean bowled by an excellent yorker from the fast bowler"          | "Gone."        |
| Six          | "What an incredible shot! The ball has sailed over the boundary for a maximum six runs!" | "Magnificent." |
| Hindi Wicket | "और वह बल्लेबाज अब आउट हो गया है गेंदबाज की शानदार गेंद पर"                                            | "गया।"          |

**Why This Matters**: Verbose AI commentary is worthless. The magic is in restraint.

---

## Document History

| Version | Date       | Author | Changes              |
| ------- | ---------- | ------ | -------------------- |
| 1.0     | 2026-01-01 | Team   | Initial architecture |

---

*"The greatest commentary is not about filling silence, but knowing when silence speaks louder."*
*— Inspired by Richie Benaud*
