# Native SwiftUI iOS App for Suksham Vachak

> **Status**: Planned
> **Created**: January 8, 2025

## Overview

Build a native iOS app using SwiftUI that connects to the existing FastAPI backend, allowing users to experience AI cricket commentary with persona selection and audio playback on their iPhone.

**Deployment**: Direct install via Xcode (FREE - no Apple Developer account needed for personal device)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SwiftUI iOS App                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────────┐   │
│  │   Views     │   │ ViewModels  │   │   Services          │   │
│  │             │   │   (MVVM)    │   │                     │   │
│  │ MatchList   │◄──│ MatchVM     │◄──│ APIClient           │   │
│  │ MomentList  │   │ MomentVM    │   │  • GET /matches     │   │
│  │ PersonaPick │   │ PersonaVM   │   │  • GET /moments     │   │
│  │ Commentary  │   │ CommentaryVM│   │  • GET /personas    │   │
│  │             │   │             │   │  • POST /commentary │   │
│  └─────────────┘   └─────────────┘   │                     │   │
│                                       │ AudioPlayer         │   │
│                                       │  • AVAudioPlayer    │   │
│                                       │  • Base64 decode    │   │
│                                       └─────────────────────┘   │
│                                                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS
                           ▼
              ┌─────────────────────────┐
              │  FastAPI Backend        │
              │  (existing)             │
              │                         │
              │  localhost:8000/api     │
              │  or Cloudflare Tunnel   │
              └─────────────────────────┘
```

---

## Project Structure

```
ios/
└── SukshamVachak/
    ├── SukshamVachakApp.swift          # App entry point
    ├── ContentView.swift               # Main navigation
    │
    ├── Models/
    │   ├── Match.swift                 # Match data model
    │   ├── Moment.swift                # Key moment model
    │   ├── Persona.swift               # Persona model
    │   └── Commentary.swift            # Request/Response types
    │
    ├── ViewModels/
    │   ├── MatchListViewModel.swift    # Fetch matches
    │   ├── MomentListViewModel.swift   # Fetch moments
    │   ├── PersonaViewModel.swift      # Persona selection
    │   └── CommentaryViewModel.swift   # Generate & play
    │
    ├── Views/
    │   ├── MatchListView.swift         # Match selection
    │   ├── MomentListView.swift        # Key moments list
    │   ├── PersonaPickerView.swift     # Persona cards
    │   ├── CommentaryView.swift        # Main commentary UI
    │   └── Components/
    │       ├── PersonaCard.swift       # Persona selection card
    │       ├── MomentRow.swift         # Moment list item
    │       └── AudioPlayerView.swift   # Playback controls
    │
    ├── Services/
    │   ├── APIClient.swift             # Network layer
    │   ├── AudioPlayerService.swift    # AVAudioPlayer wrapper
    │   └── Configuration.swift         # API base URL config
    │
    ├── Extensions/
    │   └── Color+Hex.swift             # Hex color parsing
    │
    └── Resources/
        ├── Assets.xcassets             # App icons, colors
        └── Info.plist                  # App configuration
```

---

## API Endpoints (Existing Backend)

| Endpoint                    | Method | Purpose                           |
| --------------------------- | ------ | --------------------------------- |
| `/api/health`               | GET    | Health check                      |
| `/api/matches`              | GET    | List available matches            |
| `/api/matches/{id}`         | GET    | Match details                     |
| `/api/matches/{id}/moments` | GET    | Key moments (wickets, boundaries) |
| `/api/personas`             | GET    | Available personas                |
| `/api/commentary`           | POST   | Generate commentary + audio       |

### Commentary Request/Response

```json
// Request
{
  "match_id": "1000881",
  "ball_number": "15.3",
  "persona_id": "benaud",
  "language": "en",
  "use_llm": true
}

// Response
{
  "text": "Four.",
  "audio_base64": "//uQxAAA...",
  "audio_format": "mp3",
  "persona_id": "benaud",
  "event_type": "boundary_four",
  "duration_seconds": 0.8
}
```

---

## Key Data Models

### Match.swift

```swift
struct Match: Codable, Identifiable {
    let id: String
    let teams: [String]
    let date: String
    let venue: String
    let format: String
    let winner: String
}
```

### Moment.swift

```swift
struct Moment: Codable, Identifiable {
    let id: String
    let ballNumber: String
    let innings: Int
    let eventType: String
    let batter: String
    let bowler: String
    let runs: Int
    let score: String
    let description: String
    let isWicket: Bool
    let isBoundary: Bool
}
```

### Persona.swift

```swift
struct Persona: Codable, Identifiable {
    let id: String
    let name: String
    let tagline: String
    let style: String
    let accent: String
    let language: String
    let description: String
    let color: String      // Hex color for theming
    let accentColor: String
}
```

---

## Main UI Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Match List     │────▶│  Moment List    │────▶│  Commentary     │
│                 │     │                 │     │                 │
│  • IND vs AUS   │     │  Filter:        │     │  [Persona Card] │
│  • ENG vs PAK   │     │  All|Wickets|6s │     │                 │
│  • SA vs NZ     │     │                 │     │  "Four."        │
│                 │     │  15.3 Kohli     │     │                 │
│                 │     │  16.1 Warner    │     │  ▶ ━━━●━━━ 0:02│
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                                ┌─────────────────┐
                                                │ Persona Picker  │
                                                │ (Sheet/Modal)   │
                                                │                 │
                                                │ [Benaud] [Greig]│
                                                │ [Doshi]         │
                                                └─────────────────┘
```

---

## Backend Connectivity Options

### Option A: Cloudflare Tunnel (Recommended)

```bash
# Terminal on Mac - exposes localhost to internet
cloudflared tunnel --url http://localhost:8000
# Returns: https://random-name.trycloudflare.com
```

- HTTPS (iOS requires it)
- Works anywhere, not just same WiFi
- Free, no account needed

### Option B: Local Network (Development)

```swift
// Configuration.swift
static let apiBaseURL = "http://192.168.1.xxx:8000/api"
```

- Mac and iPhone on same WiFi
- Requires updating CORS + App Transport Security

---

## Deployment to iPhone (FREE)

### Prerequisites

- Mac with Xcode 15+
- iPhone with iOS 17+
- USB cable (or WiFi pairing)

### Steps

1. **Create Xcode project**

   - File → New → Project → iOS App
   - Interface: SwiftUI
   - Language: Swift

2. **Configure signing**

   - Project → Signing & Capabilities
   - Team: "Personal Team" (your Apple ID)
   - Bundle ID: `com.yourname.sukshamvachak`

3. **Connect iPhone**

   - USB, or enable WiFi debugging

4. **First install: Trust developer**

   - iPhone: Settings → General → VPN & Device Management
   - Trust your developer certificate

5. **Build & Run** (⌘R)
   - App installs directly

### Free Tier Limitations

- App expires after 7 days (rebuild to renew)
- Max 3 apps per week
- No push notifications
- Personal use only

---

## Implementation Phases

### Phase 1: Project Setup & API Client

- [ ] Create Xcode project with SwiftUI
- [ ] Set up folder structure
- [ ] Implement `APIClient` with async/await
- [ ] Create all data models (Match, Moment, Persona, Commentary)
- [ ] Test connectivity with `/api/health`

### Phase 2: Match & Moment Views

- [ ] `MatchListView` - fetch and display matches
- [ ] `MatchListViewModel` - handle state
- [ ] `MomentListView` - show key moments with filters
- [ ] `MomentRow` component with event type styling
- [ ] Navigation between views

### Phase 3: Persona Selection

- [ ] `PersonaPickerView` - horizontal scroll cards
- [ ] `PersonaCard` component with persona colors
- [ ] `PersonaViewModel` - fetch and track selection
- [ ] Theming based on selected persona

### Phase 4: Commentary & Audio

- [ ] `CommentaryView` - main UI
- [ ] `CommentaryViewModel` - API calls, state
- [ ] `AudioPlayerService` - AVAudioPlayer wrapper
- [ ] Base64 decoding and playback
- [ ] Progress bar and controls

### Phase 5: Polish & Deploy

- [ ] Loading states and error handling
- [ ] Haptic feedback on events
- [ ] App icon and launch screen
- [ ] Cloudflare tunnel setup
- [ ] Deploy to iPhone and test

---

## Backend Changes Required

### 1. CORS (suksham_vachak/api/app.py)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow iOS app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. Run with external access

```bash
uvicorn suksham_vachak.api.app:app --host 0.0.0.0 --port 8000
```

---

## Files to Create

| Category   | Files                                                                                                          | Count        |
| ---------- | -------------------------------------------------------------------------------------------------------------- | ------------ |
| App Entry  | `SukshamVachakApp.swift`, `ContentView.swift`                                                                  | 2            |
| Models     | `Match.swift`, `Moment.swift`, `Persona.swift`, `Commentary.swift`                                             | 4            |
| ViewModels | `MatchListViewModel.swift`, `MomentListViewModel.swift`, `PersonaViewModel.swift`, `CommentaryViewModel.swift` | 4            |
| Views      | `MatchListView.swift`, `MomentListView.swift`, `PersonaPickerView.swift`, `CommentaryView.swift`               | 4            |
| Components | `PersonaCard.swift`, `MomentRow.swift`, `AudioPlayerView.swift`                                                | 3            |
| Services   | `APIClient.swift`, `AudioPlayerService.swift`, `Configuration.swift`                                           | 3            |
| Extensions | `Color+Hex.swift`                                                                                              | 1            |
| **Total**  |                                                                                                                | **21 files** |

---

## Demo Flow

1. Launch app → Match list loads
2. Tap "Australia vs India T20"
3. See key moments, filter to "Wickets"
4. Tap "15.3 - Kohli bowled Anderson"
5. Commentary view opens with Benaud selected
6. Tap "Generate" → Loading...
7. "Gone." appears with audio
8. Audio plays in Benaud's voice
9. Swipe to change persona → Greig
10. Regenerate → "He's OUT! What a delivery!"
11. Switch to Hindi → Doshi: "आउट! और गया!"

---

## Summary

| Aspect         | Choice                      |
| -------------- | --------------------------- |
| Framework      | SwiftUI (native iOS)        |
| Architecture   | MVVM                        |
| Networking     | URLSession + async/await    |
| Audio          | AVAudioPlayer               |
| Deployment     | Xcode direct install (FREE) |
| Backend Access | Cloudflare Tunnel           |
| Timeline       | 2-3 days                    |
| Files          | ~21 Swift files             |
