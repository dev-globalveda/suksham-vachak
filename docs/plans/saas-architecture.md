# Suksham Vachak - SaaS Architecture Plan

> **Document Version**: 1.0
> **Created**: January 8, 2025
> **Status**: Planning

---

## Executive Summary

Transform Suksham Vachak into a self-service platform that streaming services (Willow.tv, ESPN, Hotstar, etc.) can integrate to provide AI-powered, persona-driven cricket commentary in real-time.

---

## Business Model Options

| Model                   | Description                                     | Revenue          | Complexity |
| ----------------------- | ----------------------------------------------- | ---------------- | ---------- |
| **API-as-a-Service**    | Pay per API call (commentary generation)        | $0.001-0.01/call | Low        |
| **Subscription Tiers**  | Monthly plans with call limits                  | $99-999/month    | Medium     |
| **Revenue Share**       | % of subscriber revenue from commentary feature | 2-5% of revenue  | High       |
| **White-label License** | Full platform license for self-hosting          | $50K-500K/year   | Medium     |
| **Hybrid**              | Base subscription + overage charges             | Variable         | Medium     |

**Recommended**: Start with **API-as-a-Service** + **Subscription Tiers** for predictable revenue.

---

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INTERNET                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EDGE LAYER (Cloudflare)                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   WAF       │  │  DDoS       │  │   CDN       │  │  SSL/TLS    │        │
│  │  Protection │  │  Protection │  │  Caching    │  │  Termination│        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         API GATEWAY LAYER                                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    Kong / AWS API Gateway / Cloudflare Workers          ││
│  │  - API Key validation                                                   ││
│  │  - Rate limiting (per tenant)                                           ││
│  │  - Request routing                                                      ││
│  │  - Usage metering                                                       ││
│  │  - Request/Response transformation                                      ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          ▼                         ▼                         ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   REST API      │      │  WebSocket API  │      │  Webhook API    │
│   /v1/*         │      │  /ws/live       │      │  /v1/webhooks   │
│                 │      │                 │      │                 │
│ - Commentary    │      │ - Real-time     │      │ - Push events   │
│ - Matches       │      │ - Ball-by-ball  │      │ - Async delivery│
│ - Personas      │      │ - Subscriptions │      │ - Retry logic   │
└────────┬────────┘      └────────┬────────┘      └────────┬────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         APPLICATION LAYER                                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    Suksham Vachak Core (FastAPI)                        ││
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐      ││
│  │  │ Parser  │  │ Context │  │Commentary│  │   TTS   │  │  Stats  │      ││
│  │  │         │  │ Builder │  │  Engine │  │  Engine │  │  Engine │      ││
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘      ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                  │                                           │
│         ┌────────────────────────┼────────────────────────┐                 │
│         ▼                        ▼                        ▼                  │
│  ┌─────────────┐          ┌─────────────┐          ┌─────────────┐          │
│  │  LLM Layer  │          │  RAG Layer  │          │ Cache Layer │          │
│  │             │          │             │          │             │          │
│  │ Ollama/     │          │ ChromaDB    │          │ Redis       │          │
│  │ Claude      │          │ (moments)   │          │ (responses) │          │
│  └─────────────┘          └─────────────┘          └─────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  PostgreSQL │  │  SQLite     │  │    S3       │  │  ClickHouse │        │
│  │  (Tenants,  │  │  (Stats,    │  │  (Audio     │  │  (Analytics,│        │
│  │   Billing)  │  │   Matchups) │  │   Cache)    │  │   Metrics)  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## API Design

### REST API Endpoints

```yaml
# Base URL: https://api.sukshamvachak.com/v1

# Authentication
POST   /v1/auth/api-keys          # Create API key
GET    /v1/auth/api-keys          # List API keys
DELETE /v1/auth/api-keys/{key_id} # Revoke API key

# Commentary Generation (Core)
POST   /v1/commentary             # Generate commentary for an event
POST   /v1/commentary/batch       # Batch generation (multiple events)
POST   /v1/commentary/stream      # Server-sent events for real-time

# Match Data
GET    /v1/matches                # List available matches
GET    /v1/matches/{match_id}     # Get match details
POST   /v1/matches                # Upload custom match data (enterprise)
GET    /v1/matches/{match_id}/events # Get all events in a match

# Personas
GET    /v1/personas               # List available personas
GET    /v1/personas/{persona_id}  # Get persona details
POST   /v1/personas               # Create custom persona (enterprise)

# Audio/TTS
POST   /v1/audio/synthesize       # Generate audio from text
GET    /v1/audio/{audio_id}       # Retrieve cached audio

# Webhooks
POST   /v1/webhooks               # Register webhook endpoint
GET    /v1/webhooks               # List webhooks
DELETE /v1/webhooks/{webhook_id}  # Remove webhook

# Usage & Billing
GET    /v1/usage                  # Current usage stats
GET    /v1/usage/history          # Historical usage
GET    /v1/billing/invoices       # List invoices
```

### Request/Response Examples

```bash
# Generate Commentary
POST /v1/commentary
Authorization: Bearer sk_live_abc123
Content-Type: application/json

{
  "event": {
    "ball": "15.3",
    "batter": "V Kohli",
    "bowler": "JM Anderson",
    "runs": 4,
    "is_boundary": true,
    "match_context": {
      "score": "245/3",
      "overs": 45.3,
      "target": 320
    }
  },
  "persona": "benaud",
  "language": "en",
  "include_audio": true,
  "audio_format": "mp3"
}

# Response
{
  "id": "comm_abc123",
  "text": "Four. Kohli's timing there. Exquisite.",
  "persona": "benaud",
  "language": "en",
  "audio": {
    "url": "https://cdn.sukshamvachak.com/audio/comm_abc123.mp3",
    "duration_seconds": 2.8,
    "format": "mp3"
  },
  "context": {
    "pressure_level": "tense",
    "momentum": "batting_dominant",
    "narrative": "Kohli approaching century"
  },
  "usage": {
    "tokens": 45,
    "audio_seconds": 2.8
  }
}
```

### WebSocket API for Live Commentary

```javascript
// Client connects to WebSocket
const ws = new WebSocket("wss://api.sukshamvachak.com/v1/ws/live");

// Authenticate
ws.send(
  JSON.stringify({
    type: "auth",
    api_key: "sk_live_abc123",
  }),
);

// Subscribe to a match
ws.send(
  JSON.stringify({
    type: "subscribe",
    match_id: "IPL2025_MI_CSK_001",
    persona: "benaud",
    include_audio: true,
  }),
);

// Receive real-time commentary
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // {
  //   type: 'commentary',
  //   ball: '15.4',
  //   text: 'Gone.',
  //   audio_url: 'https://cdn...',
  //   timestamp: '2025-04-15T14:32:45Z'
  // }
};
```

---

## Multi-Tenancy Architecture

### Tenant Isolation Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TENANT ISOLATION                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Shared Infrastructure (Cost Efficient)                                      │
│  ├── API Gateway (rate limits per tenant)                                   │
│  ├── LLM Inference (queue priority by tier)                                 │
│  ├── TTS Service (shared voices)                                            │
│  └── CDN (tenant-prefixed paths)                                            │
│                                                                              │
│  Tenant-Specific Data (Isolated)                                            │
│  ├── API Keys (scoped to tenant)                                            │
│  ├── Custom Personas (enterprise only)                                      │
│  ├── Usage Metrics (per-tenant tracking)                                    │
│  ├── Cached Responses (tenant-namespaced)                                   │
│  └── Webhook Endpoints (per-tenant)                                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Database Schema (PostgreSQL)

```sql
-- Tenants (Customers)
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(63) UNIQUE NOT NULL,  -- willow-tv, espn, hotstar
    email VARCHAR(255) NOT NULL,
    tier VARCHAR(20) DEFAULT 'starter',  -- starter, pro, enterprise
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    settings JSONB DEFAULT '{}'
);

-- API Keys
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    key_hash VARCHAR(64) NOT NULL,  -- SHA-256 of the key
    key_prefix VARCHAR(12) NOT NULL,  -- sk_live_abc... (for display)
    name VARCHAR(255),
    scopes TEXT[] DEFAULT ARRAY['commentary:read'],
    rate_limit_per_minute INT DEFAULT 60,
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Usage Tracking
CREATE TABLE usage_events (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    api_key_id UUID REFERENCES api_keys(id),
    endpoint VARCHAR(100) NOT NULL,
    tokens_used INT DEFAULT 0,
    audio_seconds DECIMAL(10,2) DEFAULT 0,
    latency_ms INT,
    status_code INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create hypertable for time-series (if using TimescaleDB)
-- SELECT create_hypertable('usage_events', 'created_at');

-- Indexes
CREATE INDEX idx_usage_tenant_time ON usage_events(tenant_id, created_at DESC);
CREATE INDEX idx_api_keys_tenant ON api_keys(tenant_id);
```

---

## Subscription Tiers

| Feature              | Starter      | Pro           | Enterprise      |
| -------------------- | ------------ | ------------- | --------------- |
| **Price**            | $99/mo       | $499/mo       | Custom          |
| **API Calls**        | 10,000/mo    | 100,000/mo    | Unlimited       |
| **Audio Generation** | 1,000 min/mo | 10,000 min/mo | Unlimited       |
| **Personas**         | 3 standard   | All standard  | Custom personas |
| **Languages**        | English      | EN + Hindi    | All languages   |
| **WebSocket**        | No           | Yes           | Yes             |
| **SLA**              | None         | 99.5%         | 99.9%           |
| **Support**          | Email        | Priority      | Dedicated       |
| **Rate Limit**       | 10 req/s     | 100 req/s     | Custom          |
| **Data Retention**   | 7 days       | 30 days       | 1 year          |
| **Custom Models**    | No           | No            | Yes             |
| **On-Premise**       | No           | No            | Available       |

---

## Integration Patterns

### Pattern 1: Simple REST Integration (Willow.tv Example)

```javascript
// Willow.tv Backend
async function generateCommentary(ballEvent) {
  const response = await fetch("https://api.sukshamvachak.com/v1/commentary", {
    method: "POST",
    headers: {
      Authorization: "Bearer sk_live_willow_abc123",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      event: ballEvent,
      persona: "benaud",
      include_audio: true,
    }),
  });

  const data = await response.json();

  // Display commentary
  displayCommentary(data.text);

  // Play audio
  if (data.audio?.url) {
    playAudio(data.audio.url);
  }
}
```

### Pattern 2: Real-Time WebSocket (ESPN Example)

```javascript
// ESPN Live Match Page
class CommentaryStream {
  constructor(matchId, persona) {
    this.ws = new WebSocket("wss://api.sukshamvachak.com/v1/ws/live");
    this.matchId = matchId;
    this.persona = persona;
  }

  connect() {
    this.ws.onopen = () => {
      // Authenticate
      this.ws.send(
        JSON.stringify({
          type: "auth",
          api_key: ESPN_SUKSHAM_API_KEY,
        }),
      );

      // Subscribe to match
      this.ws.send(
        JSON.stringify({
          type: "subscribe",
          match_id: this.matchId,
          persona: this.persona,
        }),
      );
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleCommentary(data);
    };
  }

  handleCommentary(data) {
    // Update UI
    document.getElementById("commentary").innerHTML = data.text;

    // Queue audio
    if (data.audio_url) {
      this.audioQueue.push(data.audio_url);
    }
  }
}
```

### Pattern 3: Webhook Push (Hotstar Example)

```javascript
// Hotstar registers webhook
POST /v1/webhooks
{
  "url": "https://api.hotstar.com/suksham/callback",
  "events": ["commentary.generated"],
  "match_filter": {
    "format": ["T20", "IPL"],
    "teams_include": ["MI", "CSK", "RCB"]
  },
  "persona": "doshi",
  "secret": "whsec_hotstar_secret_123"
}

// Suksham Vachak POSTs to webhook
POST https://api.hotstar.com/suksham/callback
X-Suksham-Signature: sha256=abc123...
Content-Type: application/json

{
  "event": "commentary.generated",
  "data": {
    "match_id": "IPL2025_MI_CSK_001",
    "ball": "15.3",
    "text": "छक्का! क्या मारा है!",
    "audio_url": "https://cdn.sukshamvachak.com/audio/...",
    "timestamp": "2025-04-15T14:32:45Z"
  }
}
```

### Pattern 4: Embeddable Widget

```html
<!-- ESPN Article Page -->
<div
  id="suksham-commentary"
  data-match="IPL2025_MI_CSK_001"
  data-persona="benaud"
  data-theme="dark"
></div>

<script
  src="https://cdn.sukshamvachak.com/widget/v1/embed.js"
  data-api-key="pk_live_espn_public_key"
></script>
```

---

## Infrastructure Requirements

### Cloud Architecture (AWS)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS INFRASTRUCTURE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Region: ap-south-1 (Mumbai) - Primary for Indian cricket                   │
│  Region: us-east-1 (N. Virginia) - Secondary for global                     │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  Compute                                                                ││
│  │  ├── ECS Fargate (API containers) - Auto-scaling                       ││
│  │  ├── Lambda (Webhook delivery, async tasks)                            ││
│  │  └── EC2 g5.xlarge (LLM inference) - GPU instances                     ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  Data                                                                   ││
│  │  ├── RDS PostgreSQL (Multi-AZ) - Tenant data                           ││
│  │  ├── ElastiCache Redis - Caching, rate limiting                        ││
│  │  ├── S3 - Audio storage, match data                                    ││
│  │  └── DynamoDB - Session state, WebSocket connections                   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  Networking                                                             ││
│  │  ├── CloudFront - Global CDN for audio                                 ││
│  │  ├── API Gateway - REST + WebSocket APIs                               ││
│  │  ├── ALB - Load balancing                                              ││
│  │  └── VPC - Private networking                                          ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  Observability                                                          ││
│  │  ├── CloudWatch - Logs, metrics, alarms                                ││
│  │  ├── X-Ray - Distributed tracing                                       ││
│  │  └── Datadog - APM, dashboards                                         ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Cost Estimation (Monthly)

| Component           | Starter Load | Pro Load | Enterprise Load |
| ------------------- | ------------ | -------- | --------------- |
| **API Calls**       | 10K          | 100K     | 1M              |
| **ECS Fargate**     | $50          | $200     | $1,000          |
| **GPU (LLM)**       | $200         | $800     | $3,000          |
| **RDS**             | $50          | $100     | $500            |
| **Redis**           | $30          | $100     | $300            |
| **S3 + CloudFront** | $20          | $100     | $500            |
| **API Gateway**     | $10          | $50      | $200            |
| **Total**           | ~$360        | ~$1,350  | ~$5,500         |

---

## Security Architecture

### API Key Security

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         API KEY LIFECYCLE                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. Generation                                                               │
│     ├── Random 32-byte key generated                                        │
│     ├── Prefix added: sk_live_ or sk_test_                                  │
│     ├── SHA-256 hash stored in database                                     │
│     └── Full key shown ONCE to user                                         │
│                                                                              │
│  2. Validation (per request)                                                 │
│     ├── Extract key from Authorization header                               │
│     ├── Hash and lookup in database                                         │
│     ├── Check: not expired, not revoked                                     │
│     ├── Check: tenant active, within rate limit                             │
│     └── Log usage event                                                     │
│                                                                              │
│  3. Rotation                                                                 │
│     ├── Create new key                                                      │
│     ├── Grace period (both keys valid)                                      │
│     └── Revoke old key                                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Rate Limiting Strategy

```python
# Redis-based sliding window rate limiting
async def check_rate_limit(tenant_id: str, api_key_id: str) -> bool:
    key = f"ratelimit:{tenant_id}:{api_key_id}"
    window = 60  # 1 minute

    now = time.time()
    pipe = redis.pipeline()

    # Remove old entries
    pipe.zremrangebyscore(key, 0, now - window)

    # Count current window
    pipe.zcard(key)

    # Add current request
    pipe.zadd(key, {str(now): now})

    # Set expiry
    pipe.expire(key, window)

    results = await pipe.execute()
    current_count = results[1]

    # Get tenant's rate limit
    rate_limit = await get_tenant_rate_limit(tenant_id)

    return current_count < rate_limit
```

---

## Implementation Roadmap

### Phase 1: Foundation (2 weeks)

- [ ] Set up multi-tenant PostgreSQL schema
- [ ] Implement API key generation and validation
- [ ] Create `/v1/commentary` REST endpoint
- [ ] Add rate limiting middleware
- [ ] Basic usage tracking

### Phase 2: Production Ready (2 weeks)

- [ ] Add Redis caching layer
- [ ] Implement webhook delivery system
- [ ] Set up CloudFront CDN for audio
- [ ] Add Stripe billing integration
- [ ] Create tenant onboarding flow

### Phase 3: Real-Time (2 weeks)

- [ ] WebSocket API implementation
- [ ] Live match subscription system
- [ ] Connection state management
- [ ] Auto-reconnection handling

### Phase 4: Enterprise Features (2 weeks)

- [ ] Custom persona creation
- [ ] White-label options
- [ ] SLA monitoring
- [ ] Advanced analytics dashboard

### Phase 5: Scale & Optimize (Ongoing)

- [ ] Multi-region deployment
- [ ] Edge inference (Pi 5 farms)
- [ ] Cost optimization
- [ ] Performance tuning

---

## SDK Roadmap

### JavaScript/TypeScript SDK

```typescript
import { SukshamVachak } from "@suksham-vachak/sdk";

const client = new SukshamVachak({
  apiKey: "sk_live_abc123",
  persona: "benaud",
});

// Simple usage
const commentary = await client.commentary.generate({
  batter: "V Kohli",
  bowler: "JM Anderson",
  runs: 4,
  isBoundary: true,
});

// Real-time stream
const stream = client.live.subscribe("match_123");
stream.on("commentary", (data) => {
  console.log(data.text);
});
```

### Python SDK

```python
from suksham_vachak import Client

client = Client(api_key="sk_live_abc123")

# Generate commentary
result = client.commentary.generate(
    batter="V Kohli",
    bowler="JM Anderson",
    runs=4,
    is_boundary=True,
    persona="benaud"
)

print(result.text)  # "Four. Kohli's timing there. Exquisite."
```

### Swift SDK (for iOS)

```swift
import SukshamVachak

let client = SukshamVachakClient(apiKey: "sk_live_abc123")

// Generate commentary
client.generateCommentary(
    batter: "V Kohli",
    bowler: "JM Anderson",
    runs: 4,
    isBoundary: true
) { result in
    switch result {
    case .success(let commentary):
        print(commentary.text)
    case .failure(let error):
        print(error)
    }
}
```

---

## Success Metrics

| Metric         | Target (Month 1) | Target (Month 6) | Target (Year 1) |
| -------------- | ---------------- | ---------------- | --------------- |
| API Calls/Day  | 10,000           | 100,000          | 1,000,000       |
| Active Tenants | 5                | 25               | 100             |
| MRR            | $500             | $10,000          | $100,000        |
| Latency (p99)  | < 500ms          | < 300ms          | < 200ms         |
| Uptime         | 99%              | 99.5%            | 99.9%           |
| NPS            | 30               | 50               | 70              |

---

## Next Steps

1. **Validate with potential customers** - Talk to Willow.tv, Hotstar engineering
2. **Build MVP API** - Core `/v1/commentary` endpoint with API keys
3. **Create demo site** - Interactive playground for prospects
4. **Legal/Compliance** - Terms of service, privacy policy, data agreements
5. **Pricing validation** - Test pricing with early adopters

---

_"The best commentary is heard, not sold. But the platform that delivers it? That's worth paying for."_
