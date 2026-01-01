# 🚀 Suksham Vachak Prototype Build Script

> **Mental Framework for Claude CLI Engagement**
> *Target: Working MVP in 5-7 days*

---

## 🎯 The Goal

A **Streamlit demo** that shows:
1. Same cricket ball → 3 different persona commentaries
2. Same commentary → 3 different languages
3. Sliders that affect style in real-time
4. Audio output (TTS)

---

## 📋 CLI Commands Cheat Sheet

```bash
# Planning & Architecture
/plan          # Ask Claude to create a plan
/think         # Deep reasoning mode for complex problems

# Building
/build         # Generate code
/edit          # Modify existing files
/fix           # Debug issues

# Context Management
/add <file>    # Add file to context
/clear         # Clear conversation context
/compact       # Summarize and compress context

# Execution
/run           # Execute commands
/test          # Run tests
```

---

## 🗓️ Day-by-Day Script

### DAY 1: Foundation (Data + Structure)

**Session 1: Project Setup**
```
You: /plan

I'm building Suksham Vachak - an AI personalized cricket commentary platform.
Here's our vision doc: [paste key points from VISION.md]

Create a project structure for an MVP with:
- Cricket data parser (Cricsheet JSON)
- 3 personas (Benaud, Osho, Greig)
- 3 languages (English, Hindi, Tamil)
- Streamlit UI

Use Poetry for dependency management. The project exists at:
/path/to/suksham-vachak
```

**Session 2: Data Parser**
```
You: /build

Create src/data/cricket_parser.py that:
1. Loads Cricsheet JSON files from data/cricsheet_sample/
2. Extracts ball-by-ball events
3. Calculates match context (pressure, phase, milestones)
4. Returns structured data ready for commentary generation

Here's a sample JSON structure: [paste from a sample file]
```

**Session 3: Test the Parser**
```
You: /run

Run the cricket parser on the sample data.
Show me the output for one over of a match.
```

---

### DAY 2: Persona Engine

**Session 1: Base Persona**
```
You: /build

Create src/personas/base.py with:
- Persona dataclass (name, style, signature_phrases, prosody_hints)
- PersonaEngine class with generate_prompt() method
- Event type mappings (wicket, six, four, dot_ball, etc.)
```

**Session 2: Three Core Personas**
```
You: /build

Create these persona files:
1. src/personas/benaud.py - Minimalist (max 7 words, understatement)
2. src/personas/osho.py - Mystic (paradox, life lessons, pauses)
3. src/personas/greig.py - Theatrical (excitement, crescendos)

Each should have:
- Signature phrases for each event type
- Style parameters
- LLM prompt template
```

**Session 3: Test Personas**
```
You: /run

Test all 3 personas with this event:
- Kohli hits a six off Cummins
- Match situation: India need 20 from 12 balls

Show me how different each persona's output is.
```

---

### DAY 3: LLM Integration

**Session 1: Claude Client**
```
You: /build

Create src/llm/client.py that:
1. Wraps the Anthropic Claude API
2. Takes a persona + event + context
3. Returns generated commentary
4. Handles errors gracefully

Use streaming for real-time feel.
API key from environment variable: ANTHROPIC_API_KEY
```

**Session 2: Commentary Generator**
```
You: /build

Create src/llm/generator.py that:
1. Combines persona prompts with cricket events
2. Calls the LLM client
3. Post-processes the response (validate style, extract prosody hints)
4. Returns CommentaryOutput with text + metadata
```

**Session 3: End-to-End Test**
```
You: /run

Generate commentary for an entire over:
- Load a match from cricsheet_sample
- Pick one over
- Generate Benaud, Osho, Greig commentary for each ball
- Print side by side
```

---

### DAY 4: Language Layer

**Session 1: Translation Engine**
```
You: /build

Create src/languages/engine.py that:
1. Takes English commentary + persona + target language
2. Uses Claude to TRANSCREATE (not translate!)
3. Preserves style (Benaud minimalism stays minimal)
4. Returns translated text

Key rule: "Gone." in English = "गया।" in Hindi (NOT "वह आउट हो गया है")
```

**Session 2: Phrase Banks**
```
You: /build

Create pre-translated phrase banks for common phrases:
- src/languages/phrase_banks/benaud_hi.json
- src/languages/phrase_banks/benaud_ta.json
- src/languages/phrase_banks/osho_hi.json

These are for speed - no LLM call needed for common phrases.
```

**Session 3: Test Multilingual**
```
You: /run

Take Benaud's "Gone. Clean bowled." and show me:
1. Hindi version
2. Tamil version

Verify minimalism is preserved!
```

---

### DAY 5: TTS Integration

**Session 1: TTS Engine**
```
You: /build

Create src/tts/engine.py that:
1. Takes text + language + prosody hints
2. Generates SSML markup
3. Calls Google Cloud TTS (or Azure)
4. Returns audio file path

Include prosody for:
- Benaud: slow pace, long pauses
- Greig: variable pace, high excitement
- Osho: very slow, hypnotic rhythm
```

**Session 2: Audio Generation**
```
You: /run

Generate audio for the same six by Kohli:
1. Benaud English
2. Osho Hindi
3. Greig Tamil

Save as MP3 files.
```

---

### DAY 6: Streamlit UI

**Session 1: Basic App**
```
You: /build

Create mvp/app.py (Streamlit) with:
1. Match selector (dropdown of available matches)
2. Ball-by-ball display
3. Persona selector (Benaud/Osho/Greig)
4. Language selector (English/Hindi/Tamil)
5. Play button for each ball
```

**Session 2: Style Sliders**
```
You: /edit mvp/app.py

Add style sliders:
- Excitement level (0-100)
- Philosophy level (0-100)
- Poetry level (0-100)

These should affect the LLM prompt in real-time.
```

**Session 3: Audio Player**
```
You: /edit mvp/app.py

Add audio player:
- Generate audio on demand
- Play in browser
- Show loading indicator during generation
```

---

### DAY 7: Polish & Demo

**Session 1: Pre-generate Key Moments**
```
You: /run

Pre-generate audio for these iconic moments:
1. Pant's winning shot at Gabba (3 personas × 3 languages = 9 files)
2. A Kohli cover drive
3. A dramatic wicket

Save to mvp/static/audio/
```

**Session 2: Demo Script**
```
You: /plan

Create a 5-minute demo script:
1. Hook: "Watch how the same ball sounds different..."
2. Show persona switching
3. Show language switching
4. Show sliders affecting output
5. The Gabba finale
6. Close: "71 billion combinations possible"
```

**Session 3: Final Testing**
```
You: /run

Run the full Streamlit app.
Test all combinations.
Fix any bugs.
Record a backup demo video.
```

---

## 💡 Pro Tips for Claude CLI

### 1. Context is King
```
# Start each session by adding key files
/add src/data/cricket_parser.py
/add src/personas/base.py

# Then ask for the next piece
/build Create the Benaud persona following the base class pattern
```

### 2. Iterate Fast
```
# Don't aim for perfect first time
You: /build Create a basic version of X

# Then refine
You: /edit Make it handle edge case Y
You: /fix This error is happening: [paste error]
```

### 3. Use /think for Architecture Decisions
```
You: /think

Should we use Google TTS or Azure TTS?
Consider: cost, quality, Hindi support, latency, SSML support
```

### 4. Compact When Context Gets Long
```
# If conversation is getting long and slow
/compact

# This summarizes the conversation and frees up context window
```

### 5. Test Early, Test Often
```
# After every /build, immediately /run to verify
You: /build Create the parser
You: /run Test the parser with sample data

# Don't build 5 things then test - you'll lose track of bugs
```

---

## 🎯 Success Criteria

### Minimum Viable Demo
- [ ] Load cricket match data ✓
- [ ] Generate 3 different persona commentaries
- [ ] Show in at least 2 languages
- [ ] Audio plays in browser
- [ ] Sliders visibly affect output

### "Wow Factor" Moments
- [ ] Switching Benaud English → Osho Tamil is instant "wow"
- [ ] Hindi sounds natural, not robotic
- [ ] The Gabba winning moment gets emotional response

---

## 🆘 Troubleshooting

### LLM Not Following Persona Style
```
You: /think

The Benaud persona is generating 20+ word responses.
How do I make the LLM strictly follow the 7-word limit?
Consider: prompt engineering, post-processing, few-shot examples
```

### TTS Sounds Robotic
```
You: /fix

The Hindi TTS sounds flat.
Add SSML prosody tags for:
- Emphasis on key words
- Pauses before important moments
- Pitch variation for excitement
```

### Streamlit Too Slow
```
You: /think

The app is slow because we generate audio on every click.
Should we: cache, pre-generate, or use streaming?
```

---

## 📚 Quick Reference - File Locations

```
suksham-vachak/
├── src/
│   ├── data/cricket_parser.py       # Day 1
│   ├── personas/
│   │   ├── base.py                  # Day 2
│   │   ├── benaud.py                # Day 2
│   │   ├── osho.py                  # Day 2
│   │   └── greig.py                 # Day 2
│   ├── llm/
│   │   ├── client.py                # Day 3
│   │   └── generator.py             # Day 3
│   ├── languages/
│   │   ├── engine.py                # Day 4
│   │   └── phrase_banks/*.json      # Day 4
│   └── tts/
│       └── engine.py                # Day 5
├── mvp/
│   ├── app.py                       # Day 6
│   └── static/audio/                # Day 7
├── data/
│   └── cricsheet_sample/            # Already there
└── docs/
    └── VISION.md                    # Already there
```

---

## 🏁 Let's Go!

```
Day 1: Foundation  🧱
Day 2: Personas    🎭
Day 3: LLM         🤖
Day 4: Languages   🌍
Day 5: TTS         🔊
Day 6: UI          🖥️
Day 7: Polish      ✨
```

**Start Command:**
```bash
cd /path/to/suksham-vachak
claude

You: /plan Let's build Suksham Vachak MVP. Starting with Day 1 - the cricket data parser.
```

---

*"The seed was planted on December 31, 2025. Now we build the tree."* 🌱→🌳

