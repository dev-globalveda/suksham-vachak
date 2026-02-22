# ADR-022: The Commentary Singularity — North Star Architecture

**Date:** 2026-02-22

**Status:** Proposed

**Deciders:** Aman Misra

## Context

The current Suksham Vachak architecture treats commentary as a function: `(scene_class, score_text, persona) → commentary_text`. This produces serviceable output but lacks the qualities that make great human commentary transcendent — humor with timing, introspection that gives you chills, tactical challenges that make you rethink what you just saw, and visionary calls that predict what's coming.

The question is: what architectural layers are needed for an AI commentator to reach "singularity" — a state where it is simultaneously funny, introspective, challenging, and visionary, and knows _which mode to be in_ at any given moment?

This ADR captures the long-term north star vision. It is aspirational by design — not all layers will be built in v1, but every architectural decision should move toward this goal, not away from it.

## Decision

### The Four Dimensions of Singular Commentary

#### 1. Funny (हास्य — Haasya)

The ability to find humor in the moment — not scripted jokes, but contextual wit born from understanding the absurdity, irony, and joy inherent in cricket.

**What it requires:**

- **Callback memory**: "The last time Brevis faced Bumrah, he tried this exact shot and ended up in Row Z. Let's see if he's learned... no, no he has not."
- **Cultural fluency**: Bollywood references, Hindi-English code-switching, regional idioms, cricket folklore. A Basanti persona must _think_ in Basanti's world, not translate English jokes to Hindi.
- **Comic timing**: Knowing when to pause. When to let the absurdity speak for itself. When a one-liner lands vs. when it falls flat.
- **Anti-patterns**: What is NOT funny — a player's injury, a career-ending moment, a team's heartbreak. Sensitivity is not optional; it's what separates wit from cruelty.
- **Self-awareness**: The AI knowing it is AI, and occasionally playing with that. "Even my neural networks can't predict what Pant will do next."

**Exemplar personas:** Basanti, Jaspal Bhatti

#### 2. Introspective (चिंतन — Chintan)

The ability to zoom out from the action and reflect on what the moment _means_ — not just what happened, but why it matters, what it reveals about human nature, competition, and the strange beautiful game of cricket.

**What it requires:**

- **Philosophical grounding**: Drawing from traditions beyond cricket — literature, philosophy, music, life. An Osho persona doesn't just commentate; it meditates on the game.
- **Silence awareness**: Knowing when to stop talking. The moment after a wicket falls in a tense chase doesn't need words — it needs three seconds of nothing, then a quiet observation.
- **Zoom control**: Shifting between micro (this ball) and macro (this era, this rivalry, this generation of cricketers). "Kohli walks back to the pavilion, and with him, perhaps, walks an era."
- **Emotional honesty**: Not forced profundity. The introspection must arise naturally from the moment, not be imposed on it.

**Exemplar personas:** Osho, Richie Benaud

#### 3. Challenging (प्रश्न — Prashna)

The ability to question decisions, tactics, conventional wisdom, and popular narratives — not for controversy, but for truth. Great commentary holds the game accountable.

**What it requires:**

- **Deep tactical understanding**: Field placements, bowling matchups, batting matchups, game theory, phase-of-play strategy. "Why is there no slip? Bumrah has dismissed left-handers through the slip corridor 73% of the time in powerplays."
- **Statistical grounding**: Claims backed by data, not vibes. Access to historical records, player profiles, head-to-head stats.
- **Willingness to disagree**: With the captain, with the popular opinion, with the other "commentators" in the system. A challenging voice that always agrees is not challenging.
- **Intellectual honesty**: Admitting when a call was wrong. "I said the declaration was too early. I was wrong. This is masterful captaincy."

**Exemplar personas:** Tony Greig, Susheel Doshi

#### 4. Visionary (दृष्टि — Drishti)

The ability to see what's coming — not fortune-telling, but pattern recognition so deep that it feels like prophecy. Great commentators call moments before they happen.

**What it requires:**

- **Pattern recognition across eras**: "This chase has the same shape as Headingley 2019. The same deficit, the same crowd energy, the same improbability."
- **Player behavioral models**: How does a specific batsman play in the death overs when chasing? How does a bowler change their approach when hit for two consecutive boundaries?
- **Narrative arc awareness**: Every match tells a story. The visionary layer recognizes which story is being told — comeback, collapse, coronation, changing of the guard — and narrates accordingly.
- **Breakthrough detection**: Recognizing a debutant's first boundary, a veteran's twilight innings, a rivalry's turning point. "Remember this moment. You're watching the birth of something."

**Exemplar personas:** Richie Benaud, Harsha Bhogle

### The Meta-Layer: Modal Intelligence

The true singularity is not any single dimension — it is **knowing which mode to be in, moment by moment**. This requires a meta-layer that reads the emotional game state and selects the appropriate dimension:

| Game Moment                       | Primary Mode  | Why                           |
| --------------------------------- | ------------- | ----------------------------- |
| Dot ball in 3rd over              | Funny         | Low stakes, fill the air      |
| Wicket at 55/5 in WC chase        | Introspective | Weight of the moment          |
| Controversial DRS decision        | Challenging   | Accountability                |
| Debutant walks out at home ground | Visionary     | Narrative potential           |
| Hat-trick ball                    | ALL FOUR      | The moment demands everything |

This modal switching is the hardest problem. It requires understanding not just _what_ happened but _what it means in context_ — the score, the tournament stage, the players' histories, the crowd's energy, and the narrative arc of the match.

### Architectural Layers Required

```
┌─────────────────────────────────────────────┐
│           Layer 6: Modal Intelligence        │
│    "Which dimension does this moment need?"  │
├─────────────────────────────────────────────┤
│           Layer 5: Persona Synthesis         │
│    Basanti's humor × Benaud's gravitas       │
│    Dynamic persona blending per moment       │
├─────────────────────────────────────────────┤
│           Layer 4: Emotional Game State      │
│    Not just IND 55/5 but what it MEANS       │
│    Tournament context, rivalry history,       │
│    crowd energy, narrative arc               │
├─────────────────────────────────────────────┤
│           Layer 3: Memory & Recall           │
│    Cross-match, cross-series, cross-era      │
│    "Last time at this ground..."             │
│    Player career arcs, milestone tracking    │
├─────────────────────────────────────────────┤
│           Layer 2: Scene Understanding       │
│    Qwen-VL: what is happening visually       │
│    Cricket state: tactical analysis          │
│    Statistical context: historical data      │
├─────────────────────────────────────────────┤
│           Layer 1: Perception                │
│    YOLO26n: scene classification             │
│    SSIM + OCR: scorecard extraction          │
│    Audio: crowd noise level, stump mic       │
└─────────────────────────────────────────────┘
```

### Key New Components (Beyond Current Architecture)

**Emotional Game State Engine**

- Tracks not just score but _momentum_, _pressure_, _narrative tension_
- Inputs: run rate, required rate, wickets in hand, phase of play, tournament stage, head-to-head history
- Output: emotional valence (tense, euphoric, deflated, electric, poignant)

**Long-Term Memory Store**

- Cross-session memory: what happened in previous matches this tournament
- Player narrative tracking: Kohli's form this series, Bumrah's spell patterns
- Callback database: memorable moments to reference later
- Implementation: vector store (embeddings) + structured match database

**Persona Synthesis Engine**

- Current: one persona per session (Benaud OR Basanti)
- Singularity: dynamic blending. 70% Benaud gravitas + 30% Basanti energy for a tense chase that suddenly turns funny
- Personas as style vectors, not rigid templates

**Silence Model**

- Learns when NOT to speak
- Trained on broadcast analysis: when do real commentators pause?
- A wicket falling deserves 2-3 seconds of crowd noise before words
- The most powerful commentary is sometimes no commentary

**Audio Context Layer**

- Crowd noise level as emotional signal
- Stump mic audio (bat-on-ball, appeals)
- Commentary from other broadcasters (detect what's already been said, don't repeat)

## Alternatives Considered

### Pure LLM Approach (No Specialized Layers)

Feed everything to one large model and hope it figures out modal switching, timing, humor, and introspection. This fails because:

- LLMs don't have real-time game state awareness
- No memory across sessions without explicit architecture
- Humor and timing require specialized training/prompting, not general text generation
- No silence model — LLMs always want to produce output

### Scripted Template Approach

Pre-written templates for each scenario: `WICKET_TEMPLATE`, `BOUNDARY_TEMPLATE`, etc. This fails because:

- Cricket's beauty is in the unexpected
- Templates can't capture the 10,567th unique way a wicket can fall
- No emergent creativity, only recombination

## Consequences

### Positive

- **North star clarity**: Every component we build (YOLO, OCR, persona config, TTS emotion tags) has a clear purpose in the larger architecture
- **Incremental path**: Each layer can be built and tested independently. Layer 1 (perception) is already working. Layer 2 (understanding) is next. Each addition makes the system meaningfully better.
- **Unique product**: No existing system attempts this. Sports commentary AI exists, but none with modal intelligence, persona blending, and cultural fluency.

### Negative

- **Scope**: This is a multi-year vision, not a sprint
- **Evaluation**: How do you measure if commentary is "funny" or "introspective"? Human evaluation is expensive and subjective.
- **Cultural specificity**: Humor, philosophy, and cultural references don't translate across audiences. A Basanti reference is meaningless outside the Hindi-speaking world.

### Open Questions

1. **Can modal intelligence be learned or must it be engineered?** Can we train a model to select the right dimension, or do we need hand-crafted rules based on game state?
2. **How much memory is too much?** Referencing a moment from 3 matches ago is brilliant. Referencing one from 3 years ago might be confusing. Where's the line?
3. **Is the silence model technically feasible?** Detecting when to NOT generate output goes against every instinct of generative AI.
4. **Can humor be persona-specific?** Basanti-funny and Jaspal Bhatti-funny are completely different. Can one system produce both authentically?
5. **What is the minimum viable singularity?** Which two dimensions, combined, produce the biggest leap over current state-of-the-art?

## References

- ADR-021: Hybrid Vision Pipeline (YOLO26n + Qwen-VL)
- ADR-020: Cricket Emotion Tags for Svara TTS
- ADR-014: Agentic Architecture (Perceive-Reason-Remember-Plan-Act loop)
- Richie Benaud's commentary philosophy: "The greatest compliment to be paid to a commentator is that he or she has added to the viewer's enjoyment."
- Jaspal Bhatti's satirical style: finding humor in systemic absurdity, not in mocking individuals
