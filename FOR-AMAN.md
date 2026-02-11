# Suksham Vachak: The Full Story

> A guide for Aman — to understand, explain, and present this project with confidence.

---

## Part 1: The Elevator Pitch

**In one sentence**: Suksham Vachak takes raw cricket match data and turns it into persona-driven audio commentary — Richie Benaud says "Gone." while Tony Greig says "That's absolutely magnificent! Into the stands!" — for the exact same ball.

**In 30 seconds**: Cricket has 1 billion viewers but one commentary voice. We built a pipeline that reads ball-by-ball match data, builds rich situational context (pressure, momentum, narrative arcs), feeds it to an LLM with persona-specific constraints (word limits, vocabulary, cultural idioms), and synthesizes the output as audio through ElevenLabs. The whole system works in English and Hindi, with Hindi treated as _transcreation_ — not translation. Benaud's "Gone." becomes "गया।" (one word), not "वह आउट हो गया है।" (six words).

---

## Part 2: The Architecture — How It All Fits Together

Think of the system as a **restaurant kitchen**:

- The **Cricsheet JSON** is your raw ingredients (ball-by-ball match data)
- The **Parser** is the prep cook (cleans, portions, makes things usable)
- The **Context Builder** is the sous chef (combines ingredients, assesses the situation, decides the mood of the dish)
- The **Commentary Engine** is the head chef (creates the final dish based on the recipe/persona)
- The **TTS Engine** is the plating (presents the dish beautifully — as audio)

```
Cricsheet JSON ──→ Parser ──→ Context Builder ──→ Commentary Engine ──→ TTS
                                    ↓                     ↓
                    (Pressure, Momentum,        (Persona rules,
                     Narrative, Milestones)       Word limits,
                                                  LLM or Templates)
```

### The Request Lifecycle (from click to audio)

When a user clicks "Generate Commentary" in the frontend, here's exactly what happens:

1. **Frontend** sends `POST /api/commentary` with `{match_id, ball_number, persona_id, language}`

2. **Routes** (`api/routes.py:285-408`) validates everything, loads the match file

3. **Parser** (`parser/cricsheet.py`) reads the JSON, iterates through every ball in the innings

4. **Context Builder** (`context/builder.py`) processes _every ball up to the target_ — accumulating batter stats, bowler figures, partnership data, and narrative tension. This is crucial: to understand ball 15.3, you need to know everything that happened from ball 0.1 onwards.

5. **Commentary Engine** (`commentary/engine.py`) receives the event + rich context + persona, then:

   - Builds a system prompt describing who the persona is and their word limits
   - Serializes the context into TOON format (~50% fewer tokens)
   - Calls the LLM (Ollama locally, or Claude API)
   - Enforces word limits as a safety net (truncates if LLM was too verbose)

6. **TTS** (`tts/elevenlabs.py`) takes the generated text, maps the persona to a voice ID, and synthesizes audio via ElevenLabs API

7. **Response** comes back with `{text: "Gone.", audio_base64: "...", duration_seconds: 0.8}`

---

## Part 3: The Codebase Map

### Backend (`suksham_vachak/`)

```
suksham_vachak/
├── api/                    ← The front door (FastAPI endpoints)
│   ├── app.py              ← App initialization, middleware, CORS
│   └── routes.py           ← All endpoints: /matches, /personas, /commentary
│
├── parser/                 ← Raw data → structured events
│   ├── cricsheet.py        ← Reads Cricsheet JSON, yields CricketEvent objects
│   └── events.py           ← Data models: EventType, CricketEvent, MatchContext
│
├── context/                ← Building intelligence around raw events
│   ├── models.py           ← RichContext, BatterContext, BowlerContext, etc.
│   ├── builder.py          ← ContextBuilder: accumulates match state
│   ├── narrative.py        ← NarrativeTracker: storylines, callbacks
│   └── pressure.py         ← PressureCalculator: CALM → CRITICAL
│
├── commentary/             ← The brain: generating actual commentary
│   ├── engine.py           ← CommentaryEngine: LLM + template fallback
│   ├── prompts.py          ← Dynamic prompt construction per persona
│   └── providers/          ← LLM providers (Claude, Ollama)
│       ├── base.py         ← Abstract interface
│       ├── claude.py       ← Anthropic Claude
│       ├── ollama.py       ← Local Ollama models
│       └── factory.py      ← Auto-detection logic
│
├── personas/               ← Who's speaking
│   ├── base.py             ← Persona dataclass + CommentaryStyle enum
│   ├── benaud.py           ← Minimalist (0.95) — "Gone."
│   ├── greig.py            ← Dramatic (0.2) — "What a shot!"
│   └── doshi.py            ← Hindi passion (0.6) — "आउट! और गया!"
│
├── serialization/          ← Token optimization
│   └── toon_encoder.py     ← TOON format: ~50% token savings for LLM calls
│
├── tts/                    ← Text → Audio
│   ├── engine.py           ← TTSEngine: orchestrator with caching
│   ├── base.py             ← TTSProvider ABC, AudioFormat, TTSResult
│   ├── elevenlabs.py       ← ElevenLabs provider (primary)
│   ├── google.py           ← Google Cloud TTS (fallback)
│   ├── azure.py            ← Azure Speech (fallback)
│   └── prosody.py          ← SSML generation, pause/pitch/rate control
│
├── rag/                    ← Historical parallels ("reminds me of 2011...")
│   ├── retriever.py        ← DejaVuRetriever: finds similar moments
│   └── store.py            ← ChromaDB vector storage
│
└── stats/                  ← Player statistics engine
    ├── aggregator.py       ← Accumulates per-ball stats
    ├── matchups.py         ← Batter vs Bowler queries
    └── db.py               ← SQLite persistence
```

### Frontend (`frontend/`)

```
frontend/src/
├── app/
│   ├── page.tsx            ← The entire UI (match selector, persona cards,
│   │                          moment list, commentary display, audio player)
│   ├── layout.tsx          ← Root layout, fonts, metadata
│   └── globals.css         ← Dark theme, glassmorphism, gradients
├── lib/
│   └── api.ts              ← API client (fetchMatches, generateCommentary, etc.)
└── types/
    └── index.ts            ← TypeScript interfaces (Match, Persona, Moment, etc.)
```

---

## Part 4: The Key Technical Decisions (and Why)

### 1. Minimalism Score: One Number to Rule Them All

Instead of building separate commentary engines for each persona, we use a single float from 0.0 (verbose) to 1.0 (minimal) that controls _everything_:

- **Word limits per event type**: Benaud (0.95) gets 1-3 words for a wicket. Greig (0.2) gets 5-20.
- **Template selection**: High scores use MINIMAL_TEMPLATES, low scores use VERBOSE_TEMPLATES.
- **LLM max_tokens**: Minimalist personas get a 20-token budget. Verbose ones get 100.
- **SSML pauses**: Minimalists get 1.5x longer pauses (silence is part of their personality).
- **Prompt construction**: The system prompt dynamically generates word-limit rules based on this score.

**Why this matters in interviews**: This is a great example of finding the right abstraction. Instead of an explosion of if-else branches or class hierarchies, one continuous parameter controls the entire personality spectrum. It's composable, testable, and you can add new personas just by picking a number.

### 2. TOON Format: Saving Money at Scale

LLM API calls cost money per token. We built a custom serialization format called TOON (Token-Oriented Object Notation) that represents the same match context in ~50% fewer tokens:

**Before (natural language prompt)**:

```
The match is between India and Australia. The score is 145 for 3 wickets
after 23.4 overs. The current run rate is 6.18. The batter is V Kohli who
has scored 52 runs off 45 balls at a strike rate of 115.6...
```

**After (TOON format)**:

```
M
  teams [2] India, Australia
  score 145/3
  overs 23.4
  CRR 6.18
B
  name V Kohli
  runs 52
  balls 45
  SR 115.6
```

Short keys (M/B/W/P/N), no quotes, no braces, indentation-based nesting. The LLM understands both formats equally well — we just pay half the cost.

**The lesson**: Token efficiency is a real engineering concern in LLM applications. At scale, a 50% reduction in input tokens is a 50% reduction in API costs. TOON is our solution, but the broader principle is: always think about what you're sending to the LLM and whether there's a more compact representation that preserves meaning.

### 3. The Fallback Chain: Never Fail Completely

The system has three layers of fallback:

```
LLM available? → Generate with Claude/Ollama (best quality)
       ↓ no
Persona has phrase for this event? → Use signature phrase ("Gone.")
       ↓ no
Template exists? → Use template ("What a delivery!")
       ↓ no
Hardcoded fallback → "Commentary unavailable" (never happens in practice)
```

**Why**: Users should never see a blank screen. Even if the internet is down and Ollama isn't running, the system produces _something_. This is graceful degradation — the quality drops, but the system doesn't break.

**Real-world analogy**: It's like a restaurant. If the head chef is sick (LLM down), the sous chef takes over (templates). If even the sous chef isn't there, the prep cook makes you a sandwich (signature phrases). You never leave hungry.

### 4. Context Building: Processing History to Understand the Present

To generate commentary for ball 15.3, we don't just look at that one delivery. The `ContextBuilder` processes every ball from 0.1 to 15.3, accumulating:

- **Batter stats**: 52 off 45 balls, approaching a fifty, settled (20+ balls)
- **Bowler stats**: 2 wickets, economy 7.84, bowling well
- **Partnership**: 78 runs together, batter-dominant
- **Pressure**: INTENSE (death overs, high required rate)
- **Narrative**: "partnership_building" storyline, high tension, batting momentum

This gives the LLM the context to say "Kohli approaches his fifty under immense pressure" rather than just "Hit for four."

**The lesson**: Commentary isn't about the ball — it's about the _story_. Good engineering recognizes that the same data point (a four) means completely different things at 20/0 in the 3rd over versus 245/8 in the 49th. Context transforms data into narrative.

### 5. Auto LLM Detection: Be Smart About What's Available

```python
def create_llm_provider(provider_name: str = "auto"):
    if provider_name == "auto":
        # 1. Try Ollama (free, local, no API key needed)
        if _is_ollama_running():
            return OllamaProvider()
        # 2. Try Claude (paid, but high quality)
        if os.environ.get("ANTHROPIC_API_KEY"):
            return ClaudeProvider()
        # 3. No LLM available — engine will use templates
        raise ValueError("No LLM provider available")
```

**Why Ollama first**: During development, you don't want to burn API credits for every test. Ollama runs locally, is free, and is fast enough for development. Claude is the production choice for quality. The system figures out what's available and uses the best option.

### 6. Transcreation, Not Translation

This isn't just a technical decision — it's a philosophical one. When Benaud says "Gone." in English, the Hindi version must be "गया।" (one word), not "वह आउट हो गया है।" (six words). Translation preserves meaning; transcreation preserves _style_.

The system achieves this by:

- Making Doshi a native Hindi persona (not Benaud translated)
- Using Hindi idioms in `emotion_range` (culturally natural expressions)
- Separate word limits for Hindi output (same constraints, different language)
- Telling the LLM explicitly: "You ARE Sushil Doshi. You speak Hindi natively."

---

## Part 5: The Technology Stack (and Why Each Choice)

| Layer         | Technology           | Why This One                                                                                          |
| ------------- | -------------------- | ----------------------------------------------------------------------------------------------------- |
| Backend       | **FastAPI**          | Async by default, auto-generates OpenAPI docs, Pydantic validation built-in, fastest Python framework |
| LLM (quality) | **Claude API**       | Best at following complex persona instructions, strong at creative writing, good multilingual         |
| LLM (dev)     | **Ollama**           | Free, local, fast iteration without API costs. Qwen 2.5 7B is surprisingly good                       |
| TTS           | **ElevenLabs**       | Best voice quality, multilingual support, simple API. Voices sound human, not robotic                 |
| Frontend      | **Next.js**          | React SSR, great DX, easy deployment. App Router for modern patterns                                  |
| Styling       | **Tailwind**         | Utility-first = fast prototyping, no naming fatigue, responsive out of the box                        |
| Animation     | **Framer Motion**    | Declarative animations in React, great for persona color transitions                                  |
| Serialization | **TOON**             | Custom format for token efficiency. ~50% savings on every LLM call                                    |
| Data          | **Cricsheet JSON**   | The gold standard for cricket data. Ball-by-ball, 17K+ matches, open source                           |
| Type checking | **Pyright (strict)** | Catches bugs before runtime. Strict mode means no `Any` types sneaking in                             |
| Linting       | **Ruff**             | 10-100x faster than flake8+black combined. One tool for linting AND formatting                        |
| Testing       | **pytest**           | De facto standard. Fixtures, parametrize, markers — everything you need                               |

### Technologies That Didn't Make the Cut

| Rejected                          | Why                                                                                               |
| --------------------------------- | ------------------------------------------------------------------------------------------------- |
| **Streamlit** (for frontend)      | Too limited for the UI we needed. No fine-grained control over layout, animations, or audio.      |
| **GPT-4** (for LLM)               | Claude follows persona instructions more reliably. GPT tends to be verbose regardless of prompts. |
| **Google Cloud TTS** (as primary) | Voices sound robotic compared to ElevenLabs. Kept as fallback.                                    |
| **Redis** (for caching)           | Overkill for MVP. Frontend Map cache + TTS file cache is sufficient.                              |
| **Kafka** (for streaming)         | Not needed until live match integration. Currently post-match replay only.                        |
| **SQLAlchemy** (for DB)           | Raw SQLite with custom queries is simpler for stats aggregation. No ORM overhead.                 |

---

## Part 6: Design Patterns In Action

### 1. Strategy Pattern (TTS Providers)

```python
class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text, voice_id, language) -> TTSResult: ...

class ElevenLabsTTSProvider(TTSProvider):
    def synthesize(self, text, voice_id, language) -> TTSResult:
        # ElevenLabs-specific implementation

class GoogleTTSProvider(TTSProvider):
    def synthesize(self, text, voice_id, language) -> TTSResult:
        # Google-specific implementation
```

**Why**: Swap providers without changing calling code. The `TTSEngine` doesn't know or care which provider it's using — it just calls `synthesize()`.

### 2. Factory Pattern (LLM Provider Selection)

```python
def create_llm_provider(provider_name: str = "auto") -> BaseLLMProvider:
    if provider_name == "ollama":
        return OllamaProvider()
    elif provider_name == "claude":
        return ClaudeProvider()
    elif provider_name == "auto":
        # Try each in priority order
        ...
```

**Why**: The route handler doesn't need to know about provider initialization details. It just asks for "auto" and gets whatever's available.

### 3. Builder Pattern (Context Building)

```python
builder = ContextBuilder(match_info)
for event in parser.parse_innings(1):
    context = builder.build(event)  # Accumulates state
# Final context has full match history
```

**Why**: Context is accumulated incrementally. Each `build()` call adds to the running state (batter stats, partnerships, pressure). The builder encapsulates the complexity of tracking 300+ balls of state.

### 4. Iterator Pattern (Parsing)

```python
def parse_innings(self, innings_number=1) -> Iterator[CricketEvent]:
    for over in innings["overs"]:
        for delivery in over["deliveries"]:
            yield CricketEvent(...)  # Memory efficient
```

**Why**: A T20 innings has ~120 balls, an ODI has ~300, a Test can have 1000+. Yielding events one-by-one means constant memory usage regardless of match length.

### 5. Dataclass as Configuration Objects

```python
@dataclass
class Persona:
    name: str
    style: CommentaryStyle
    minimalism_score: float
    emotion_range: dict[str, str]
    ...
```

**Why**: Personas are immutable configuration. No inheritance hierarchy, no complex behavior — just data. New personas are created by instantiating the same class with different values. This is "composition over inheritance" in practice.

---

## Part 7: Lessons, Bugs, and Engineering Wisdom

### Lesson 1: Pre-commit Hooks Will Save Your Life (After They Drive You Crazy)

**The bug**: Commits kept failing because `prettier` was reformatting markdown/JSON files during the commit hook, which meant the staged files changed mid-commit.

**The fix**: Run `poetry run pre-commit run --all-files` _before_ `git commit`, not during. Format first, then commit the already-formatted files.

**The principle**: Pre-commit hooks should _verify_, not _modify_. If they modify files, you get a chicken-and-egg problem. Our workflow: format → stage → commit (hooks verify, pass cleanly).

### Lesson 2: LLMs Don't Follow Instructions as Well as You Think

**The bug**: Benaud persona was supposed to say 1-3 words. Claude would sometimes return "Gone. What a magnificent delivery that was, catching the edge beautifully." — the persona leaked into verbosity.

**The fix**: Word-limit enforcement at the engine level. After the LLM responds, `_enforce_word_limit()` truncates to the allowed count and adds a period. Belt-and-suspenders approach: the prompt _asks_ for brevity, the code _enforces_ it.

**The principle**: Never trust LLM output to match your constraints. Always validate/enforce programmatically. LLMs are probabilistic — they'll follow instructions 90% of the time, which means they'll violate them 10% of the time. That 10% is what your users will notice.

### Lesson 3: The Empty String is a Feature

**The discovery**: Benaud doesn't comment on dot balls. Silence IS his commentary. The `emotion_range` for `dot_ball` is `""` (empty string).

**The lesson**: In commentary, silence is as powerful as words. This is a design insight that translates to engineering: the absence of output is a valid output. Don't force every event to produce text. A minimalist commentator's silence says "nothing interesting happened" more eloquently than "Well, that was a dot ball."

### Lesson 4: Context Is Everything (Literally)

**The problem**: Early prototype generated commentary like "Hit for four" regardless of match situation. A four at 20/0 feels routine. A four at 245/8 needing 6 to win is _historic_.

**The solution**: RichContext accumulates the entire match state. The LLM receives pressure level, narrative tension, milestone proximity, and momentum direction. Now the same four generates "Marvellous." (calm situation, Benaud) or "THAT COULD BE THE MATCH!" (tense chase, Greig).

**The principle**: Raw data without context is meaningless. This applies everywhere: a 500ms response time means nothing without knowing the baseline. A test failure means nothing without knowing what changed. Always provide context.

### Lesson 5: Token Efficiency is a First-Class Concern

**The numbers**: Claude charges per token. A verbose match context prompt is ~800 tokens. The same information in TOON format is ~400 tokens. Over thousands of API calls, that's a 50% cost reduction.

**The implementation**: TOON encoder strips quotes, uses single-letter keys (M/B/W/P), uses indentation instead of braces, and only includes non-null fields.

**The principle**: In LLM applications, your prompt IS your product. Optimizing it is like optimizing a database query — it doesn't change the result, but it changes the cost and speed dramatically. Always ask: "Can I represent this more compactly without losing meaning?"

### Lesson 6: Auto-Detection Beats Configuration

**The problem**: Developers need to set `LLM_PROVIDER=ollama` locally and `LLM_PROVIDER=claude` in production. People forget, things break.

**The solution**: `provider="auto"` tries Ollama first (local dev default), falls back to Claude (production default). Zero configuration needed for the common case.

**The principle**: The best configuration is no configuration. Smart defaults > explicit settings. If you can detect the right answer, do it automatically. Only ask the user to configure when you genuinely can't figure it out.

### Lesson 7: Cache at the Right Layer

**The caching strategy**:

- **Frontend**: Commentary cache (`matchId-ballNumber-personaId-language` → response). Instant persona switching without re-calling the API.
- **TTS Engine**: SHA256-based file cache. Same text + same voice = same audio. Don't re-synthesize.
- **System Prompt**: Cached per persona+toon combination. Don't rebuild the same string 1000 times.

**The principle**: Cache where the cost is. LLM calls are expensive → cache results. TTS calls are slow → cache audio. Prompt building is cheap → cache for cleanliness, not performance. Know your bottlenecks.

### Lesson 8: Graceful Degradation Over Hard Failures

**The pattern everywhere**:

- No LLM? Use templates. No templates? Use persona phrases. No phrases? Use hardcoded fallbacks.
- No ElevenLabs? Try Google TTS. No Google? Return text without audio.
- No Cricsheet data? Use sample data. No sample data? Return 404 (only at this point).

**The principle**: Every external dependency is a potential failure point. Design your system so that each failure _reduces quality_ rather than _breaking the system_. Users prefer a worse experience over no experience.

### Lesson 9: The Event-to-Emotion Map is the Key Insight

```python
EVENT_EMOTION_MAP = {
    EventType.WICKET: "wicket",
    EventType.BOUNDARY_SIX: "boundary_six",
    EventType.BOUNDARY_FOUR: "boundary_four",
    EventType.DOT_BALL: "dot_ball",
    ...
}
```

**Why this matters**: This tiny mapping is the bridge between _data_ (event types from the parser) and _personality_ (emotion phrases from the persona). Without it, the persona system would need to understand cricket event types. With it, personas only need to know emotions.

**The principle**: Adapter layers between domains keep each domain clean. The parser doesn't know about emotions. The persona doesn't know about event types. The mapping bridges them without coupling them.

### Lesson 10: Pyright Strict Mode is Worth the Pain

**The pain**: Every function needs return type annotations. Every variable needs explicit types when not inferrable. No `Any` types. No untyped third-party libraries without stubs.

**The payoff**: Caught bugs before they happened. A function returning `Optional[str]` forced us to handle the `None` case. A `dict[str, str]` annotation caught a `dict[str, int]` being passed. Type errors are compile-time bugs, not runtime crashes.

**The principle**: Strong typing is documentation that the compiler enforces. In a project with multiple modules calling each other, types are the contract between modules. Break the contract → the type checker tells you immediately, not your users.

---

## Part 8: What Good Engineers Do (Lessons from Building This)

### 1. Start with the Data Model

We didn't start by building the UI or the LLM integration. We started with `CricketEvent` — what does a single delivery look like as a data structure? Then `MatchContext` — what's the match state? Then `RichContext` — what does the LLM need to know?

**Principle**: Get your data models right first. Everything else (UI, APIs, storage) is just transforming and transporting those models. If the model is wrong, everything built on top is wrong.

### 2. Make the Common Case Easy, the Uncommon Case Possible

- Common case: Generate commentary with auto-detected LLM → one function call
- Uncommon case: Specify provider, disable TOON, use a specific language → optional parameters
- Rare case: Add a new TTS provider → implement the `TTSProvider` ABC

### 3. Fail Fast, Fail Loud

```python
if not match_file.exists():
    raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
```

Don't silently return empty results or let errors propagate as mysterious None values. If something's wrong, say so immediately and specifically.

### 4. Separate Concerns Ruthlessly

- Parser knows about JSON → Events
- Context knows about Events → Situational awareness
- Commentary knows about Context + Persona → Text
- TTS knows about Text → Audio
- Routes know about HTTP → orchestration

No module does two jobs. If you find yourself importing from 5 different modules in one function, you're probably doing too much.

### 5. Test the Boundaries, Not the Internals

Our tests focus on:

- Does the parser produce correct `CricketEvent` objects from known JSON?
- Does the context builder detect "struggling batter" correctly?
- Does TOON encoding preserve all information?
- Does word-limit enforcement actually truncate?

We don't test internal helper functions unless they have complex logic. Test the contract, not the implementation.

### 6. Write Code That Reads Like a Story

```python
# Good: you can read the intent
commentary = engine.generate(event, persona)
if not commentary.text:
    commentary.text = get_fallback(language)
audio = tts.synthesize(commentary.text, persona)

# Bad: what is this doing?
r = e.gen(ev, p)
if not r.t:
    r.t = fb(l)
a = t.s(r.t, p)
```

Variable names, function names, module names — they should tell a story. Someone reading your code for the first time should understand the _intent_ without reading comments.

---

## Part 9: Interview-Ready Talking Points

### "Tell me about a technical challenge you solved"

> "Our LLM would sometimes ignore word-limit constraints for the minimalist persona. Benaud should say 'Gone.' but Claude would sometimes add extra description. We solved this with a two-layer approach: the prompt specifies word limits, and the engine enforces them programmatically after generation. This taught me that LLMs are probabilistic — you can't trust them to always follow instructions, so you need programmatic guardrails."

### "How do you handle system failures?"

> "We built a three-layer fallback chain. If the LLM is unavailable, we fall back to templates. If templates don't cover the event, we use persona signature phrases. If even that fails, we have hardcoded per-language fallbacks. The system degrades gracefully — quality drops, but it never breaks. For TTS, we have primary (ElevenLabs) and fallback (Google) providers with automatic retry."

### "How do you optimize for cost?"

> "We built a custom serialization format called TOON that represents the same match context in roughly half the tokens. LLM APIs charge per token, so this is a direct 50% cost reduction on every API call. We also cache aggressively — generated commentary is cached by match+ball+persona+language, and TTS audio is cached by content hash. Same inputs never hit the API twice."

### "Explain a design decision you're proud of"

> "The minimalism score. Instead of building separate commentary engines for each persona, we use a single float (0.0 to 1.0) that controls word limits, template selection, LLM token budgets, and even SSML pause lengths. Adding a new persona means picking a number on this spectrum. It's simple, extensible, and avoids a class explosion."

### "How do you handle multilingual content?"

> "We distinguish between translation and transcreation. Translation preserves meaning but destroys style — Benaud's 'Gone.' becomes a six-word Hindi sentence. Transcreation preserves style — 'Gone.' becomes 'गया।' (one word). We achieve this by making Hindi personas genuinely Hindi, not English personas that output Hindi. Doshi speaks Hindi idioms naturally, with culturally appropriate cricket expressions."

### "What would you do differently?"

> "Three things: (1) I'd add streaming for the LLM response — right now we wait for the full response before displaying. SSE streaming would show text appearing in real-time. (2) I'd build a proper evaluation pipeline earlier — we don't have automated quality metrics for generated commentary yet. (3) I'd use WebSocket for TTS — streaming audio chunks instead of waiting for the full synthesis."

### "How does the system scale?"

> "The stateless API design means horizontal scaling is trivial — add more FastAPI instances behind a load balancer. The expensive calls (LLM, TTS) are idempotent and cacheable. The context builder is the only stateful component per request, but it only lives for the duration of one request. For the full 17K match dataset, we'd need a proper database instead of filesystem scanning, but that's a straightforward migration."

---

## Part 10: Potential Pitfalls and How to Avoid Them

### Pitfall 1: LLM Temperature and Persona Drift

**Problem**: At higher temperatures, the LLM gets creative and "forgets" it's supposed to be minimalist. At lower temperatures, it becomes repetitive.

**Solution**: Keep temperature at 0.7 for creative variety, but enforce word limits programmatically. The LLM's job is creativity within constraints; the code's job is enforcing those constraints.

### Pitfall 2: Context Window Overflow

**Problem**: In Test matches (5 days, 1000+ balls), processing every ball to build context could overflow the LLM's context window.

**Solution**: TOON format keeps the _prompt_ small regardless of match length. The context builder only sends the _current state_ (accumulated stats), not the full history. A batter's context is "52 off 45 balls" — not a replay of all 45 deliveries.

### Pitfall 3: TTS Costs at Scale

**Problem**: ElevenLabs charges per character. Generating audio for every ball in every match gets expensive fast.

**Solution**: Cache aggressively (SHA256 key: text + voice + format). Never synthesize the same text twice. Consider local TTS alternatives (Qwen3-TTS) for development.

### Pitfall 4: Stale Match Data

**Problem**: Cricsheet updates their dataset regularly. Our sample data is a snapshot.

**Solution**: The parser is format-agnostic within Cricsheet's schema. Drop new JSON files into `data/all_male_json/` and they're immediately available. No migration needed.

### Pitfall 5: CORS and Environment Mismatch

**Problem**: Frontend on `localhost:3000`, backend on `localhost:8000`. Browser blocks cross-origin requests.

**Solution**: `CORSMiddleware` in `app.py` explicitly allows `localhost:3000`. In production, this would be the actual domain. The env variable `NEXT_PUBLIC_API_URL` lets the frontend know where the backend lives.

---

## Part 11: The Numbers

| Metric                      | Value                                   |
| --------------------------- | --------------------------------------- |
| Python modules              | 25+                                     |
| API endpoints               | 8                                       |
| Test files                  | 9                                       |
| Personas (live)             | 3                                       |
| Languages (live)            | 2 (English, Hindi)                      |
| Cricsheet matches available | 17,020                                  |
| Sample matches in repo      | 20                                      |
| TTS providers supported     | 3 (ElevenLabs, Google, Azure)           |
| LLM providers supported     | 2 (Claude, Ollama)                      |
| Token savings with TOON     | ~50%                                    |
| Fallback layers             | 4 (LLM → template → phrase → hardcoded) |

---

## Part 12: What's Next (If You Continued Building)

1. **Streaming responses** — SSE for text, WebSocket for audio chunks
2. **Evaluation pipeline** — Automated quality metrics (word count compliance, persona consistency, cultural appropriateness)
3. **More personas** — Osho, Harsha Bhogle, Feynman (defined but not implemented)
4. **Fine-tuned models** — LoRA adapters on Qwen/Llama trained on our own commentary output
5. **Live match integration** — Real-time data feeds instead of post-match replay
6. **Voice cloning** — Custom ElevenLabs voices from real commentator audio
7. **More languages** — Tamil, Bengali, Telugu using the same transcreation approach

---

## The One-Line Summary

**Suksham Vachak is a lesson in constraint-driven design**: the minimalism score constrains the LLM, TOON constrains the token count, word limits constrain the output, and persona definitions constrain the vocabulary — and from all those constraints emerges something that sounds natural, personal, and alive.

That's the paradox of good engineering: the more precisely you define the boundaries, the more creative the system becomes within them.
