# Suksham Vachak - Implementation Guide

> Step-by-step implementation plans for each phase of the cricket commentary engine.

---

## Phase 1: Context Builder

### Overview

Build a rich context system that transforms raw cricket events into meaningful situational awareness for LLM commentary generation.

**Key Insight:** Great commentary isn't about describing what happened—it's about understanding what it _means_. A wicket in the 3rd over is different from a wicket in the 19th over.

### Module Structure

```
suksham_vachak/context/
├── __init__.py              # Module exports
├── models.py                # Dataclasses and enums
├── builder.py               # ContextBuilder orchestrator
├── pressure.py              # PressureCalculator
└── narrative.py             # NarrativeTracker
```

### Implementation Steps

#### Step 1: Core Enums (`models.py`)

Define the vocabulary of match situations:

```python
class MatchPhase(Enum):
    POWERPLAY = "powerplay"
    MIDDLE_OVERS = "middle_overs"
    DEATH_OVERS = "death_overs"
    EARLY_INNINGS = "early_innings"   # Test matches
    MIDDLE_INNINGS = "middle_innings"
    LATE_INNINGS = "late_innings"

class PressureLevel(Enum):
    CALM = "calm"           # 0.0-0.2
    BUILDING = "building"   # 0.2-0.4
    TENSE = "tense"         # 0.4-0.6
    INTENSE = "intense"     # 0.6-0.8
    CRITICAL = "critical"   # 0.8-1.0

class MomentumState(Enum):
    BATTING_DOMINANT = "batting_dominant"
    BOWLING_DOMINANT = "bowling_dominant"
    BALANCED = "balanced"
    MOMENTUM_SHIFT = "momentum_shift"
```

#### Step 2: Player Context Dataclasses (`models.py`)

Track individual player states:

```python
@dataclass
class BatterContext:
    name: str
    runs_scored: int
    balls_faced: int
    strike_rate: float
    fours: int
    sixes: int
    approaching_milestone: str | None  # "50", "100"
    recent_scoring: list[int]          # Last 6 balls
    dot_ball_pressure: int             # Consecutive dots

    @property
    def is_new_batter(self) -> bool:
        return self.balls_faced < 10

    @property
    def is_settled(self) -> bool:
        return self.balls_faced >= 20 and self.strike_rate >= 80

    @property
    def is_struggling(self) -> bool:
        return self.balls_faced >= 15 and self.strike_rate < 60

@dataclass
class BowlerContext:
    name: str
    overs_bowled: float
    maidens: int
    runs_conceded: int
    wickets: int
    economy: float
    current_spell_wickets: int
    recent_deliveries: list[str]  # "W", "4", ".", "1"
    is_on_hat_trick: bool
    consecutive_dots: int
```

#### Step 3: Match Situation (`models.py`)

Capture the overall game state:

```python
@dataclass
class MatchSituation:
    batting_team: str
    bowling_team: str
    total_runs: int
    total_wickets: int
    overs_completed: float
    phase: MatchPhase
    match_format: str
    target: int | None = None
    runs_required: int | None = None
    required_rate: float | None = None
    current_run_rate: float = 0.0

    @property
    def is_chase(self) -> bool:
        return self.target is not None

    @property
    def is_close_chase(self) -> bool:
        if not self.is_chase or self.required_rate is None:
            return False
        return abs(self.required_rate - self.current_run_rate) < 2.0
```

#### Step 4: Pressure Calculator (`pressure.py`)

Quantify match pressure (0.0 to 1.0):

```python
class PressureCalculator:
    PHASE_BASE_PRESSURE = {
        MatchPhase.POWERPLAY: 0.3,
        MatchPhase.MIDDLE_OVERS: 0.2,
        MatchPhase.DEATH_OVERS: 0.5,
    }

    def calculate(self, match, wickets_recent, is_new_batter, balls_since_boundary):
        pressure = self.PHASE_BASE_PRESSURE.get(match.phase, 0.2)

        # Chase pressure
        if match.is_chase and match.required_rate:
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

#### Step 5: Narrative Tracker (`narrative.py`)

Track the story of the match:

```python
class NarrativeTracker:
    def update(self, event, batter_runs, bowler_wickets, partnership_runs):
        # Detect momentum
        if self._consecutive_boundaries >= 3:
            momentum = MomentumState.BATTING_DOMINANT
        elif self._consecutive_dots >= 6:
            momentum = MomentumState.BOWLING_DOMINANT

        # Build storyline
        storyline = self._build_storyline(event)

        # Detect subplots
        subplot = None
        if 45 <= batter_runs < 50:
            subplot = f"{event.batter} 5 away from fifty"

        return NarrativeState(
            current_storyline=storyline,
            momentum=momentum,
            key_subplot=subplot,
            callbacks_available=self._get_callbacks(event)
        )
```

#### Step 6: Context Builder (`builder.py`)

Orchestrate everything:

```python
class ContextBuilder:
    def __init__(self, match_info):
        self.pressure_calc = PressureCalculator()
        self.narrative_tracker = NarrativeTracker()
        # State tracking for batters, bowlers, partnerships...

    def build(self, event: CricketEvent) -> RichContext:
        self._update_state(event)

        match_situation = self._build_match_situation(event)
        batter_context = self._build_batter_context(event)
        bowler_context = self._build_bowler_context(event)
        partnership = self._build_partnership_context()

        pressure_level, pressure_score = self.pressure_calc.calculate(...)
        narrative = self.narrative_tracker.update(...)

        return RichContext(
            event=event,
            match=match_situation,
            batter=batter_context,
            bowler=bowler_context,
            partnership=partnership,
            narrative=narrative,
            pressure=pressure_level,
            suggested_tone=self._determine_tone(event, pressure_level),
            suggested_length=self._determine_length(event),
        )
```

#### Step 7: Prompt Context Output (`models.py`)

Format for LLM consumption:

```python
class RichContext:
    def to_prompt_context(self) -> str:
        """
        Output format:
        === MATCH SITUATION ===
        India vs Australia
        Score: 156/4 (18.2)
        Phase: death_overs

        === BATTER ===
        V Kohli: 47 (35), SR: 134.3
        Approaching: 50
        Status: Well set

        === NARRATIVE ===
        Storyline: Batters on top
        Momentum: batting_dominant
        Tension: High

        === PRESSURE: INTENSE ===
        """
```

### Files Created

| File                    | Lines | Purpose                          |
| ----------------------- | ----- | -------------------------------- |
| `context/__init__.py`   | ~20   | Module exports                   |
| `context/models.py`     | ~330  | Dataclasses and enums            |
| `context/builder.py`    | ~540  | State tracking and orchestration |
| `context/pressure.py`   | ~160  | Pressure calculation             |
| `context/narrative.py`  | ~310  | Storyline and momentum tracking  |
| `tests/test_context.py` | ~300  | Unit tests                       |

### Verification

```bash
# Run context tests
poetry run pytest tests/test_context.py -v

# Test with sample match
python -c "
from suksham_vachak.parser import CricsheetParser
from suksham_vachak.context import ContextBuilder

parser = CricsheetParser('data/cricsheet_sample/1000881.json')
builder = ContextBuilder(parser.match_info)

for event in parser.parse_innings(1):
    ctx = builder.build(event)
    if event.is_wicket:
        print(ctx.to_prompt_context())
        break
"
```

---

## Phase 2: LLM Commentary Engine

### Overview

Generate persona-driven commentary using Claude LLM with the rich context from Phase 1.

**Key Insight:** The persona constrains the LLM. Benaud says "Four." while Greig says "Tremendous shot! The crowd erupts!" Same event, different style.

### Module Structure

```
suksham_vachak/commentary/
├── __init__.py              # Module exports
├── engine.py                # CommentaryEngine orchestrator
├── prompts.py               # Prompt templates
└── llm.py                   # Claude API client

suksham_vachak/personas/
├── __init__.py
├── base.py                  # Persona dataclass
├── benaud.py                # Richie Benaud (minimalist)
├── greig.py                 # Tony Greig (dramatic)
└── doshi.py                 # Sushil Doshi (Hindi)
```

### Implementation Steps

#### Step 1: Persona Definition (`personas/base.py`)

```python
@dataclass
class Persona:
    id: str
    name: str
    description: str
    language: str
    voice_style: str
    minimalism_score: float  # 0.0 (verbose) to 1.0 (minimal)
    emotion_range: dict[str, str]  # event_type -> emotion
    signature_phrases: list[str]
    word_limits: dict[str, tuple[int, int]]  # event_type -> (min, max)

    @property
    def is_minimalist(self) -> bool:
        return self.minimalism_score >= 0.8
```

#### Step 2: Define Personas

**Benaud (minimalist):**

```python
BENAUD = Persona(
    id="benaud",
    name="Richie Benaud",
    minimalism_score=0.95,
    word_limits={
        "wicket": (1, 3),
        "boundary_six": (1, 3),
        "boundary_four": (1, 2),
        "dot_ball": (0, 0),  # Silence
    },
    signature_phrases=[
        "Marvellous.",
        "Gone.",
        "Magnificent.",
    ],
)
```

**Greig (dramatic):**

```python
GREIG = Persona(
    id="greig",
    name="Tony Greig",
    minimalism_score=0.20,
    word_limits={
        "wicket": (10, 25),
        "boundary_six": (8, 20),
        "boundary_four": (5, 15),
        "dot_ball": (3, 10),
    },
    signature_phrases=[
        "Tremendous!",
        "The crowd goes wild!",
    ],
)
```

#### Step 3: LLM Client (`llm.py`)

```python
class LLMClient:
    MODELS = {
        "haiku": "claude-3-haiku-20240307",
        "sonnet": "claude-sonnet-4-20250514",
        "opus": "claude-opus-4-20250514",
    }

    def __init__(self, model: str = "haiku"):
        self.client = anthropic.Anthropic()
        self.model = self.MODELS[model]

    def complete(self, system_prompt: str, user_prompt: str, max_tokens: int = 100):
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return LLMResponse(
            text=response.content[0].text,
            model=self.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
```

#### Step 4: Prompt Building (`prompts.py`)

**System Prompt:**

```python
def build_system_prompt(persona: Persona) -> str:
    return f"""You are {persona.name}, the legendary cricket commentator.

Style: {persona.description}

Your signature phrases include:
{chr(10).join(f'- "{p}"' for p in persona.signature_phrases[:8])}

CRITICAL RULES:
- Maximum {persona.word_limits.get('wicket', (1, 10))[1]} words for wickets
- Maximum {persona.word_limits.get('boundary_six', (1, 10))[1]} words for sixes
- {'Silence is golden. Say nothing for dot balls.' if persona.is_minimalist else ''}

BAD (too verbose): "What an incredible shot! The ball has sailed over the boundary!"
GOOD: "{persona.signature_phrases[0] if persona.signature_phrases else 'Magnificent.'}"
"""
```

**Rich Context Prompt:**

```python
def build_rich_context_prompt(rich_context: RichContext, persona: Persona) -> str:
    context_text = rich_context.to_prompt_context()
    return f"""{context_text}

Generate commentary as {persona.name}.
Tone: {rich_context.suggested_tone}
Length: {rich_context.suggested_length}
"""
```

#### Step 5: Commentary Engine (`engine.py`)

```python
class CommentaryEngine:
    def __init__(self, use_llm: bool = True, context_builder: ContextBuilder | None = None):
        self.use_llm = use_llm
        self.context_builder = context_builder
        self.llm_client = LLMClient() if use_llm else None

    def generate(self, event: CricketEvent, persona: Persona, language: str = "en") -> Commentary:
        # Build rich context
        rich_context = None
        if self.context_builder:
            rich_context = self.context_builder.build(event)

        if self.use_llm and self.llm_client:
            return self._generate_with_llm(event, persona, language, rich_context)
        else:
            return self._generate_with_templates(event, persona)

    def _generate_with_llm(self, event, persona, language, rich_context):
        system_prompt = build_system_prompt(persona)

        if rich_context:
            user_prompt = build_rich_context_prompt(rich_context, persona)
        else:
            user_prompt = build_event_prompt(event, persona)

        max_tokens = 20 if persona.is_minimalist else 100

        response = self.llm_client.complete(system_prompt, user_prompt, max_tokens)

        # Enforce word limits as safety net
        text = self._enforce_word_limit(response.text, event, persona)

        return Commentary(
            text=text,
            persona_id=persona.id,
            event_type=event.event_type,
            rich_context=rich_context,
        )
```

#### Step 6: API Integration (`api/routes.py`)

```python
@router.post("/api/commentary")
async def generate_commentary(request: CommentaryRequest):
    parser = CricsheetParser(f"data/cricsheet_sample/{request.match_id}.json")
    context_builder = ContextBuilder(parser.match_info)

    engine = CommentaryEngine(use_llm=request.use_llm, context_builder=context_builder)

    # Find the target ball
    for event in parser.parse_all_innings():
        if event.ball_number == request.ball_number:
            commentary = engine.generate(event, get_persona(request.persona_id))
            return CommentaryResponse(
                text=commentary.text,
                persona_id=commentary.persona_id,
                event_type=event.event_type.value,
            )
```

### The Benaud Test

Every implementation must pass:

| Scenario     | ❌ Fail                                | ✅ Pass        |
| ------------ | -------------------------------------- | -------------- |
| Wicket       | "The batsman has been clean bowled..." | "Gone."        |
| Six          | "What an incredible shot! The ball..." | "Magnificent." |
| Hindi Wicket | "और वह बल्लेबाज अब आउट हो गया है..."   | "गया।"         |

### Files Created

| File                     | Lines | Purpose                 |
| ------------------------ | ----- | ----------------------- |
| `commentary/__init__.py` | ~15   | Module exports          |
| `commentary/engine.py`   | ~375  | Generation orchestrator |
| `commentary/prompts.py`  | ~230  | Prompt templates        |
| `commentary/llm.py`      | ~100  | Claude API wrapper      |
| `personas/base.py`       | ~50   | Persona dataclass       |
| `personas/benaud.py`     | ~80   | Benaud persona          |
| `personas/greig.py`      | ~80   | Greig persona           |
| `personas/doshi.py`      | ~80   | Doshi persona (Hindi)   |

### Verification

```bash
# Run demo script
python demo_llm_commentary.py

# Expected output:
# Ball 0.1: FOUR! - "Four."
# Ball 0.4: SIX! - "Magnificent."
# Ball 2.3: WICKET! - "Gone."
```

---

## Phase 3: RAG "Déjà Vu Engine"

### Overview

Add historical context retrieval to commentary system, enabling "reminds me of..." moments.

**Tech Stack:**

- Vector DB: ChromaDB (lightweight, Raspberry Pi-friendly)
- Embeddings: Anthropic Voyage API
- Data: Sample Cricsheet matches + curated iconic moments

### Branch

```bash
git checkout -b feature/phase-3-rag
```

### New Module Structure

```
suksham_vachak/rag/
├── __init__.py              # Module exports
├── models.py                # CricketMoment, RetrievedMoment dataclasses
├── embeddings.py            # VoyageEmbeddingClient
├── store.py                 # MomentVectorStore (ChromaDB wrapper)
├── retriever.py             # DejaVuRetriever (query orchestration)
├── config.py                # RAGConfig dataclass
├── cli.py                   # CLI for ingestion/management
└── ingestion/
    ├── __init__.py
    ├── cricsheet.py         # Parse matches → moments
    └── curated.py           # Load YAML → moments

data/
├── curated/
│   └── iconic_moments.yaml  # Hand-curated ~10-20 iconic moments
└── vector_db/               # ChromaDB persistent storage
    └── .gitkeep
```

### Implementation Steps

#### Step 1: Create branch and add dependencies

- Create `feature/phase-3-rag` branch
- Add to pyproject.toml: `chromadb = "^0.4.0"`
- Add env var: `VOYAGE_API_KEY`

#### Step 2: Data Models (`rag/models.py`)

- `MomentType` enum: wicket, milestone, boundary_spree, clutch, iconic, etc.
- `MomentSource` enum: cricsheet, curated
- `CricketMoment` dataclass with:
  - Match context (id, format, date, teams, venue)
  - Situation (score, wickets, phase, pressure, momentum)
  - Players (primary, secondary, fielder)
  - Narrative (description, significance)
  - `to_embedding_text()` → composite text for vectorization
  - `to_metadata()` → dict for ChromaDB
- `RetrievedMoment` with similarity score and `to_callback_string()`

#### Step 3: Voyage Embeddings (`rag/embeddings.py`)

- `VoyageEmbeddingClient` class
- Methods: `embed_documents()`, `embed_query()`
- Uses httpx for API calls
- Model: `voyage-2` (or `voyage-lite-02-instruct` for Pi)

#### Step 4: ChromaDB Store (`rag/store.py`)

- `MomentVectorStore` class
- Methods: `add_moments()`, `query()`, `query_by_player()`, `query_by_situation()`
- Curated moment boost (1.5x score multiplier)
- Persistent storage in `data/vector_db/`

#### Step 5: Retriever (`rag/retriever.py`)

- `DejaVuRetriever` class
- Multi-strategy retrieval:
  1. Player-based: find moments with same batter/bowler
  2. Situation-based: similar pressure/phase/momentum
  3. Format-based: prefer same format (T20/ODI/Test)
- Deduplication and ranking
- Returns `list[str]` formatted as callbacks

#### Step 6: Ingestion Pipeline

- `CricsheetIngester`: Parse all balls, extract wickets/boundaries/milestones
- `CuratedIngester`: Load from `iconic_moments.yaml`
- CLI: `python -m suksham_vachak.rag.cli ingest`

#### Step 7: Curated Moments (`data/curated/iconic_moments.yaml`)

Initial ~10-15 iconic moments:

- Sachin's Desert Storm (1998)
- Kapil's 175 (1983 WC)
- Dhoni's WC2011 winning six
- Stokes at Headingley (2019)
- Yuvraj's 6 sixes (2007)
- Kohli vs Pakistan T20 WC (2022)
- etc.

#### Step 8: Integration with ContextBuilder

**Modify:** `suksham_vachak/context/builder.py`

- Add optional `rag_retriever` parameter to `__init__`
- In `build()`: call retriever and merge callbacks

```python
if self.rag_retriever:
    historical = self.rag_retriever.retrieve(event, match, pressure)
    narrative_state.callbacks_available = historical + narrative_state.callbacks_available
```

#### Step 9: Enhanced Prompt Output

**Modify:** `suksham_vachak/context/models.py`

- Update `NarrativeState.to_prompt_context()` to show "Memory Lane:" section

```
=== NARRATIVE ===
Storyline: ...
Memory Lane:
  - History: Dhoni's WC2011 winning six (India vs Sri Lanka, 2011-04-02)
  - Earlier: Kohli hit boundary off Bumrah (15.2)
```

#### Step 10: Update API routes (optional)

**Modify:** `suksham_vachak/api/routes.py`

- Initialize RAG retriever if VOYAGE_API_KEY is set
- Pass to ContextBuilder

#### Step 11: Tests (`tests/test_rag.py`)

- Mock embedding client for unit tests
- Test moment serialization
- Test store add/query
- Test retriever deduplication
- Test curated boost

#### Step 12: Documentation

- Update `docs/ARCHITECTURE.md` with RAG section
- Update D2 diagram with Déjà Vu Engine

### Files to Modify

| File                                | Change                      |
| ----------------------------------- | --------------------------- |
| `pyproject.toml`                    | Add chromadb dependency     |
| `.env.example`                      | Add VOYAGE_API_KEY          |
| `suksham_vachak/context/builder.py` | Add rag_retriever param     |
| `suksham_vachak/context/models.py`  | Enhance to_prompt_context() |
| `suksham_vachak/api/routes.py`      | Initialize RAG (optional)   |

### Files to Create

| File                                        | Purpose             |
| ------------------------------------------- | ------------------- |
| `suksham_vachak/rag/__init__.py`            | Module exports      |
| `suksham_vachak/rag/models.py`              | Data models         |
| `suksham_vachak/rag/embeddings.py`          | Voyage client       |
| `suksham_vachak/rag/store.py`               | ChromaDB wrapper    |
| `suksham_vachak/rag/retriever.py`           | Query orchestration |
| `suksham_vachak/rag/config.py`              | Configuration       |
| `suksham_vachak/rag/cli.py`                 | Ingestion CLI       |
| `suksham_vachak/rag/ingestion/__init__.py`  | Ingestion module    |
| `suksham_vachak/rag/ingestion/cricsheet.py` | Cricsheet parser    |
| `suksham_vachak/rag/ingestion/curated.py`   | YAML loader         |
| `data/curated/iconic_moments.yaml`          | Curated moments     |
| `data/vector_db/.gitkeep`                   | DB directory        |
| `tests/test_rag.py`                         | Unit tests          |

### Environment Variables

```bash
# Add to .env
VOYAGE_API_KEY=pa-...  # Get from voyageai.com
```

### Verification

After implementation:

```bash
# Ingest data
python -m suksham_vachak.rag.cli ingest

# Check stats
python -m suksham_vachak.rag.cli stats

# Test commentary with RAG
python demo_llm_commentary.py
# Should see "History: ..." in narrative section
```

---

## Future Phases

### Phase 4: Stats Engine

- Player tendency analysis
- Matchup statistics
- Venue/conditions analysis
- Historical averages

### Phase 5: Forecasting

- Next ball probability prediction
- Win probability model
- What-if scenario analysis
- Field placement suggestions

---

## Document History

| Version | Date       | Author | Changes                       |
| ------- | ---------- | ------ | ----------------------------- |
| 1.0     | 2026-01-05 | Team   | Initial guide with Phases 1-3 |
