# Suksham Vachak - System Architecture

> **Document Version**: 2.0
> **Last Updated**: January 5, 2026
> **Status**: Phases 1 & 2 Complete, Phase 3 (RAG) Next

---

## Executive Summary

Suksham Vachak is a personalized AI cricket commentary platform that generates authentic, persona-driven commentary from match data. The system uses LLMs with rich situational context to produce commentary that captures each commentator's unique style.

**What's Working Now**:

- Parse Cricsheet JSON matches
- Build rich context (pressure, momentum, narrative)
- Generate LLM-powered commentary in multiple personas
- Convert to speech with persona-appropriate prosody
- Web frontend with persona/language selection

**Key Differentiator**: The Context Builder provides the LLM with deep situational awareness - not just "what happened" but "what it means" (pressure level, momentum shifts, storylines, player form).

---

## Current Architecture (Phases 1 & 2 Complete)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SUKSHAM VACHAK - CURRENT SYSTEM                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────────────────────────┐ │
│  │  Cricsheet  │───→│   Cricket   │───→│         CONTEXT BUILDER          │ │
│  │    JSON     │    │   Parser    │    │  ┌────────────────────────────┐  │ │
│  │             │    │             │    │  │     Match Situation        │  │ │
│  │ • Ball-by-  │    │ • Events    │    │  │  • Score, overs, phase     │  │ │
│  │   ball data │    │ • Context   │    │  │  • Target, required rate   │  │ │
│  │ • Players   │    │ • Match     │    │  └────────────────────────────┘  │ │
│  │ • Outcomes  │    │   info      │    │  ┌────────────────────────────┐  │ │
│  └─────────────┘    └─────────────┘    │  │     Player Context         │  │ │
│                                         │  │  • Batter: runs, SR, form  │  │ │
│                                         │  │  • Bowler: spell, economy  │  │ │
│                                         │  │  • Partnership: runs, RR   │  │ │
│                                         │  └────────────────────────────┘  │ │
│                                         │  ┌────────────────────────────┐  │ │
│                                         │  │    Pressure Calculator     │  │ │
│                                         │  │  • Phase-based pressure    │  │ │
│                                         │  │  • Chase pressure          │  │ │
│                                         │  │  • Wicket cluster pressure │  │ │
│                                         │  └────────────────────────────┘  │ │
│                                         │  ┌────────────────────────────┐  │ │
│                                         │  │    Narrative Tracker       │  │ │
│                                         │  │  • Storylines              │  │ │
│                                         │  │  • Momentum shifts         │  │ │
│                                         │  │  • Subplots (milestones)   │  │ │
│                                         │  └────────────────────────────┘  │ │
│                                         └────────────────┬─────────────────┘ │
│                                                          │                   │
│                                                          ▼                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                       COMMENTARY ENGINE                               │   │
│  │  ┌─────────────────┐   ┌─────────────────┐   ┌──────────────────┐   │   │
│  │  │  PERSONA LAYER  │   │  PROMPT BUILDER │   │   LLM (Claude)   │   │   │
│  │  │ ┌─────────────┐ │   │                 │   │                  │   │   │
│  │  │ │   Benaud    │ │──→│  Rich Context   │──→│  Haiku/Sonnet    │   │   │
│  │  │ │ minimalist  │ │   │  + Persona      │   │                  │   │   │
│  │  │ └─────────────┘ │   │  + Guidelines   │   │  Output:         │   │   │
│  │  │ ┌─────────────┐ │   │                 │   │  "Four."         │   │   │
│  │  │ │   Greig     │ │   │                 │   │  "Magnificent!"  │   │   │
│  │  │ │  dramatic   │ │   │                 │   │  "कमाल का शॉट!"   │   │   │
│  │  │ └─────────────┘ │   │                 │   │                  │   │   │
│  │  │ ┌─────────────┐ │   │                 │   │                  │   │   │
│  │  │ │   Doshi     │ │   │                 │   │                  │   │   │
│  │  │ │   Hindi     │ │   │                 │   │                  │   │   │
│  │  │ └─────────────┘ │   │                 │   │                  │   │   │
│  │  └─────────────────┘   └─────────────────┘   └────────┬─────────┘   │   │
│  └───────────────────────────────────────────────────────┼─────────────┘   │
│                                                          │                  │
│                                                          ▼                  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         TTS ENGINE                                    │  │
│  │  ┌─────────────────┐   ┌─────────────────┐   ┌──────────────────┐   │  │
│  │  │ VOICE SELECTOR  │   │ PROSODY CONTROL │   │  GOOGLE CLOUD    │   │  │
│  │  │                 │   │                 │   │     TTS          │   │  │
│  │  │ Benaud → en-AU  │──→│  Wicket: pause  │──→│                  │   │  │
│  │  │ Greig  → en-GB  │   │  Six: excited   │   │  WaveNet voices  │   │  │
│  │  │ Doshi  → hi-IN  │   │  Dot: subdued   │   │  SSML support    │   │  │
│  │  └─────────────────┘   └─────────────────┘   └────────┬─────────┘   │  │
│  └───────────────────────────────────────────────────────┼─────────────┘  │
│                                                          │                 │
│                                                          ▼                 │
│                                                 ┌─────────────────┐        │
│                                                 │  AUDIO OUTPUT   │        │
│                                                 │  • MP3 stream   │        │
│                                                 │  • Base64 API   │        │
│                                                 └─────────────────┘        │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Module Deep Dive

### 1. Context Builder (`suksham_vachak/context/`)

The Context Builder is the brain of the system. It transforms raw cricket events into rich situational context that enables intelligent commentary.

#### 1.1 Models (`models.py`)

```python
# Match Phases - Different game situations
class MatchPhase(Enum):
    POWERPLAY = "powerplay"        # Overs 1-6 (T20/ODI)
    MIDDLE_OVERS = "middle_overs"  # Overs 7-15 (T20)
    DEATH_OVERS = "death_overs"    # Final overs
    EARLY_INNINGS = "early_innings"
    LATE_INNINGS = "late_innings"

# Pressure Levels - How tense is the situation?
class PressureLevel(Enum):
    CALM = "calm"           # Score: 0.0-0.2
    BUILDING = "building"   # Score: 0.2-0.4
    TENSE = "tense"         # Score: 0.4-0.6
    INTENSE = "intense"     # Score: 0.6-0.8
    CRITICAL = "critical"   # Score: 0.8-1.0

# Momentum - Who's on top?
class MomentumState(Enum):
    BATTING_DOMINANT = "batting_dominant"
    BOWLING_DOMINANT = "bowling_dominant"
    BALANCED = "balanced"
    MOMENTUM_SHIFT = "momentum_shift"

# Player Contexts
@dataclass
class BatterContext:
    name: str
    runs_scored: int
    balls_faced: int
    strike_rate: float
    approaching_milestone: str | None  # "50", "100"
    is_new_batter: bool      # < 10 balls
    is_settled: bool         # 20+ balls, good SR
    is_struggling: bool      # 15+ balls, low SR
    dot_ball_pressure: int   # Consecutive dots

@dataclass
class BowlerContext:
    name: str
    overs_bowled: float
    wickets: int
    economy: float
    current_spell_wickets: int
    is_on_hat_trick: bool
    is_bowling_well: bool
    consecutive_dots: int

# The Complete Context
@dataclass
class RichContext:
    event: CricketEvent
    match: MatchSituation
    batter: BatterContext
    bowler: BowlerContext
    partnership: PartnershipContext
    recent: RecentEvents
    narrative: NarrativeState
    pressure: PressureLevel
    pressure_score: float  # 0.0-1.0
    suggested_tone: str    # "calm", "excited", "tense", "dramatic"
    suggested_length: str  # "short", "medium", "long"
    avoid_phrases: list[str]  # Recently used phrases

    def to_prompt_context(self) -> str:
        """Convert to text for LLM prompt."""
        # Returns structured text like:
        # === MATCH SITUATION ===
        # India vs Australia
        # Score: 156/4 (18.2)
        # Phase: death_overs
        #
        # === BATTER ===
        # V Kohli: 47 (35), SR: 134.3
        # Approaching: 50
        # Status: Well set
        # ...
```

#### 1.2 Pressure Calculator (`pressure.py`)

Calculates match pressure based on multiple factors:

```python
class PressureCalculator:
    # Base pressure by match phase
    PHASE_BASE_PRESSURE = {
        MatchPhase.POWERPLAY: 0.3,
        MatchPhase.MIDDLE_OVERS: 0.2,
        MatchPhase.DEATH_OVERS: 0.5,  # Higher base
    }

    def calculate(self, match, wickets_recent, is_new_batter, balls_since_boundary):
        pressure = 0.0

        # Phase pressure
        pressure += self.PHASE_BASE_PRESSURE[match.phase]

        # Chase pressure (required rate vs current rate)
        if match.is_chase:
            rate_diff = match.required_rate - match.current_run_rate
            if rate_diff > 0:
                pressure += min(0.3, rate_diff * 0.05)

        # Wicket cluster (collapse)
        if wickets_recent >= 3:
            pressure += 0.2

        # New batter vulnerability
        if is_new_batter:
            pressure += 0.1

        # Dot ball tension
        if balls_since_boundary > 12:
            pressure += min(0.15, (balls_since_boundary - 12) * 0.01)

        return clamp(pressure, 0.0, 1.0)
```

#### 1.3 Narrative Tracker (`narrative.py`)

Tracks the story of the match:

```python
class NarrativeTracker:
    def update(self, event, batter_runs, bowler_wickets, partnership):
        # Detect momentum shifts
        if consecutive_boundaries >= 3:
            momentum = MomentumState.BATTING_DOMINANT
        elif consecutive_dots >= 6:
            momentum = MomentumState.BOWLING_DOMINANT

        # Build storyline
        if event.is_wicket and wickets_in_spell >= 2:
            storyline = f"{event.bowler} is wreaking havoc!"
        elif consecutive_boundaries >= 3:
            storyline = f"Boundaries flowing! {event.batter} taking control"

        # Detect subplots (milestones approaching)
        if 45 <= batter_runs < 50:
            subplot = f"{event.batter} 5 away from fifty"

        return NarrativeState(
            current_storyline=storyline,
            tension_level=tension,
            momentum=momentum,
            key_subplot=subplot,
            dramatic_potential="Century beckons" if batter_runs >= 95 else None
        )
```

---

### 2. Commentary Engine (`suksham_vachak/commentary/`)

Generates text commentary using LLM with persona constraints.

```python
class CommentaryEngine:
    def __init__(self, use_llm=True, context_builder=None):
        self.use_llm = use_llm
        self.context_builder = context_builder
        self.llm_client = LLMClient()

    def generate(self, event, persona):
        # Build rich context
        if self.context_builder:
            rich_context = self.context_builder.build(event)

        # Build prompt with context
        system_prompt = build_system_prompt(persona)
        user_prompt = build_rich_context_prompt(rich_context, persona)

        # LLM generates commentary
        response = self.llm_client.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=20 if persona.is_minimalist else 100
        )

        return Commentary(
            text=response.text,
            rich_context=rich_context,
            used_llm=True
        )
```

#### Persona-Specific Outputs

| Event  | Benaud (minimalist=0.95) | Greig (minimalist=0.20)              | Doshi (Hindi)          |
| ------ | ------------------------ | ------------------------------------ | ---------------------- |
| FOUR   | "Four."                  | "Tremendous shot! The crowd erupts!" | "चौका! शानदार!"        |
| SIX    | "Magnificent."           | "That's gone all the way! Maximum!"  | "छक्का! क्या मारा है!" |
| WICKET | "Gone."                  | "He's OUT! What a moment!"           | "आउट! और गया!"         |
| DOT    | _(silence)_              | "Good delivery from Cummins."        | ""                     |

---

### 3. TTS Pipeline (`suksham_vachak/tts/`)

Converts commentary to speech with emotional prosody.

```python
class ProsodyController:
    EVENT_PROSODY = {
        EventType.WICKET: {
            "rate": "slow",      # Dramatic pause
            "pitch": "+2st",     # Slightly higher
            "break_before": "500ms"
        },
        EventType.BOUNDARY_SIX: {
            "rate": "fast",      # Excited
            "pitch": "+4st",     # Much higher
            "volume": "loud"
        },
        EventType.DOT_BALL: {
            "rate": "medium",
            "pitch": "-1st",     # Subdued
            "volume": "soft"
        }
    }

    def apply_prosody(self, text, persona, event_type):
        # Generate SSML with prosody
        return f"""
        <speak>
            <prosody rate="{rate}" pitch="{pitch}">
                {escaped_text}
            </prosody>
        </speak>
        """
```

---

## Data Flow

```
┌─────────────┐
│  Cricsheet  │
│    JSON     │
└──────┬──────┘
       │
       ▼
┌─────────────┐     For each ball:
│   Parser    │     ──────────────────────────────────────────────────────────
└──────┬──────┘                                                               │
       │                                                                      │
       ▼                                                                      │
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐  │
│   Context   │────→│  Pressure   │────→│  Narrative  │────→│    Rich     │  │
│   Builder   │     │ Calculator  │     │  Tracker    │     │   Context   │  │
└─────────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘  │
                                                                   │         │
       ┌───────────────────────────────────────────────────────────┘         │
       │                                                                      │
       ▼                                                                      │
┌─────────────┐     ┌─────────────┐     ┌─────────────┐                      │
│   Prompt    │────→│     LLM     │────→│ Commentary  │                      │
│   Builder   │     │  (Claude)   │     │    Text     │                      │
└─────────────┘     └─────────────┘     └──────┬──────┘                      │
                                               │                              │
       ┌───────────────────────────────────────┘                              │
       │                                                                      │
       ▼                                                                      │
┌─────────────┐     ┌─────────────┐     ┌─────────────┐                      │
│   Prosody   │────→│  Google TTS │────→│   Audio     │                      │
│   Control   │     │  (WaveNet)  │     │   Output    │──────────────────────┘
└─────────────┘     └─────────────┘     └─────────────┘
```

---

## API Reference

### POST /api/commentary

Generate commentary for a specific moment.

**Request**:

```json
{
  "match_id": "1000881",
  "ball_number": "15.3",
  "persona_id": "benaud",
  "language": "en",
  "use_llm": true
}
```

**Response**:

```json
{
  "text": "Four.",
  "audio_base64": "//uQxAAAAAANIAAAAAE...",
  "audio_format": "mp3",
  "persona_id": "benaud",
  "event_type": "boundary_four",
  "duration_seconds": 0.8
}
```

---

## Directory Structure

```
suksham-vachak/
├── suksham_vachak/
│   ├── __init__.py
│   ├── parser/
│   │   ├── __init__.py
│   │   ├── cricsheet.py        # Cricsheet JSON parser
│   │   └── events.py           # CricketEvent, MatchContext
│   ├── context/                # NEW: Context module
│   │   ├── __init__.py
│   │   ├── models.py           # RichContext, enums, dataclasses
│   │   ├── builder.py          # ContextBuilder
│   │   ├── pressure.py         # PressureCalculator
│   │   └── narrative.py        # NarrativeTracker
│   ├── commentary/
│   │   ├── __init__.py
│   │   ├── engine.py           # CommentaryEngine
│   │   ├── prompts.py          # System/event prompts
│   │   └── llm.py              # Claude API client
│   ├── personas/
│   │   ├── __init__.py
│   │   ├── base.py             # Persona dataclass
│   │   ├── benaud.py           # Richie Benaud
│   │   ├── greig.py            # Tony Greig
│   │   └── doshi.py            # Sushil Doshi
│   ├── tts/
│   │   ├── __init__.py
│   │   ├── base.py             # TTSProvider base
│   │   ├── google.py           # Google Cloud TTS
│   │   └── prosody.py          # SSML prosody control
│   └── api/
│       ├── __init__.py
│       ├── app.py              # FastAPI app
│       └── routes.py           # API endpoints
├── frontend/                   # Next.js frontend
│   └── src/
│       └── app/
│           └── page.tsx        # Main UI
├── data/
│   └── cricsheet_sample/       # Sample match data
├── tests/
│   ├── test_parser.py
│   ├── test_context.py         # NEW: Context tests
│   ├── test_commentary.py
│   └── test_tts.py
├── demo_llm_commentary.py      # CLI demo script
└── docs/
    ├── ARCHITECTURE.md         # This file
    ├── VISION.md
    └── ROADMAP.md
```

---

## Development Roadmap

### ✅ Phase 1: Context Builder (Complete)

- [x] MatchPhase, PressureLevel, MomentumState enums
- [x] BatterContext, BowlerContext, PartnershipContext
- [x] PressureCalculator with multi-factor scoring
- [x] NarrativeTracker for storylines and subplots
- [x] ContextBuilder aggregating all context
- [x] RichContext.to_prompt_context() for LLM

### ✅ Phase 2: LLM Commentary (Complete)

- [x] CommentaryEngine with context_builder support
- [x] build_rich_context_prompt() for enhanced prompts
- [x] API routes using context-aware generation
- [x] Demo script (demo_llm_commentary.py)
- [x] Persona-specific outputs working

### 🔜 Phase 3: RAG - Déjà Vu Engine (Next)

- [ ] Vector database for historical moments
- [ ] Embed match situations for similarity search
- [ ] "This reminds me of..." retrieval
- [ ] Player comparison retrieval
- [ ] Classic match callbacks

### 📋 Phase 4: Stats Engine

- [ ] Player tendency analysis
- [ ] Matchup statistics
- [ ] Venue/conditions analysis
- [ ] Historical averages

### 📋 Phase 5: Forecasting

- [ ] Next ball probability prediction
- [ ] Win probability model
- [ ] What-if scenario analysis
- [ ] Field placement suggestions

---

## The Benaud Test

Every implementation must pass the Benaud Test:

| Scenario     | ❌ Fail                                                                                  | ✅ Pass        |
| ------------ | ---------------------------------------------------------------------------------------- | -------------- |
| Wicket       | "The batsman has been clean bowled by an excellent yorker from the fast bowler"          | "Gone."        |
| Six          | "What an incredible shot! The ball has sailed over the boundary for a maximum six runs!" | "Magnificent." |
| Hindi Wicket | "और वह बल्लेबाज अब आउट हो गया है गेंदबाज की शानदार गेंद पर"                              | "गया।"         |

**Why This Matters**: Verbose AI commentary is worthless. The magic is in restraint.

---

## Document History

| Version | Date       | Author | Changes                                    |
| ------- | ---------- | ------ | ------------------------------------------ |
| 1.0     | 2026-01-01 | Team   | Initial architecture                       |
| 2.0     | 2026-01-05 | Team   | Phase 1 & 2 complete, Context Builder docs |

---

_"The greatest commentary is not about filling silence, but knowing when silence speaks louder."_
_— Inspired by Richie Benaud_
