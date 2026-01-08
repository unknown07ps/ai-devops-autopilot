# Deployr AI DevOps Autopilot - System Architecture & Dataflow
# ============================================================
# Comprehensive guide for testing and deployment planning

## 🏗️ High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DEPLOYR ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────────────────── FRONTEND ────────────────────────────┐           │
│  │                     Deployr_dashboard.html                        │           │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │           │
│  │  │  Control    │ │  Incidents  │ │   Actions   │ │Intelligence │ │           │
│  │  │   Center    │ │     View    │ │     View    │ │    Panel    │ │           │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │           │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │           │
│  │  │ Autonomous  │ │Cloud Costs  │ │Subscription │ │   Runbooks  │ │           │
│  │  │    Mode     │ │  Dashboard  │ │  & Billing  │ │  Automation │ │           │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘ │           │
│  └───────────────────────────────────────────────────────────────────┘           │
│                                       │                                          │
│                                       │ HTTP/REST                                │
│                                       ▼                                          │
│  ┌──────────────────────────── API LAYER ────────────────────────────┐          │
│  │                        FastAPI (src/main.py)                       │          │
│  │                           Port: 8000                               │          │
│  │  ┌───────────────────────────────────────────────────────────────┐ │          │
│  │  │ ROUTERS:                                                      │ │          │
│  │  │ • auth_api.py      → /api/auth/*     (Login, Register, JWT)  │ │          │
│  │  │ • subscription_api → /api/subscription/* (Plans, Billing)    │ │          │
│  │  │ • dashboard_api    → /api/dashboard/*    (Stats, Services)   │ │          │
│  │  │ • razorpay_api     → /api/razorpay/*     (Payment Gateway)   │ │          │
│  │  │ • suppression_api  → /api/suppression/*  (Alert Rules)       │ │          │
│  │  │ • slack_interactive→ /api/slack/*        (Slack Webhooks)    │ │          │
│  │  └───────────────────────────────────────────────────────────────┘ │          │
│  └────────────────────────────────────────────────────────────────────┘          │
│                                       │                                          │
│           ┌───────────────────────────┼───────────────────────────┐              │
│           │                           │                           │              │
│           ▼                           ▼                           ▼              │
│  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐          │
│  │   POSTGRESQL    │      │      REDIS      │      │     OLLAMA      │          │
│  │   (Database)    │      │  (Event Queue)  │      │   (AI/LLM)      │          │
│  │   Port: 5432    │      │   Port: 6379    │      │  Port: 11434    │          │
│  │                 │      │                 │      │                 │          │
│  │ • Users         │      │ • Event Streams │      │ • llama3        │          │
│  │ • Subscriptions │      │ • Metrics Cache │      │ • Incident      │          │
│  │ • API Keys      │      │ • Baselines     │      │   Analysis      │          │
│  │ • Sessions      │      │ • Incidents     │      │ • Root Cause    │          │
│  └─────────────────┘      └─────────────────┘      └─────────────────┘          │
│                                       │                                          │
│                                       ▼                                          │
│  ┌──────────────────────── BACKGROUND WORKERS ───────────────────────┐          │
│  │                                                                    │          │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │          │
│  │  │   worker.py  │  │worker_phase2 │  │worker_phase3 │            │          │
│  │  │  (Basic)     │  │  (Enhanced)  │  │ (Autonomous) │            │          │
│  │  └──────────────┘  └──────────────┘  └──────────────┘            │          │
│  │                                                                    │          │
│  │  ┌──────────────────────────────────────────────────────────┐    │          │
│  │  │ SCHEDULED JOBS (APScheduler):                            │    │          │
│  │  │ • Trial expiration check (daily @ midnight)              │    │          │
│  │  │ • Trial reminder emails (daily @ 9 AM)                   │    │          │
│  │  │ • Session cleanup (every 6 hours)                        │    │          │
│  │  │ • Subscription expiration check                          │    │          │
│  │  └──────────────────────────────────────────────────────────┘    │          │
│  └────────────────────────────────────────────────────────────────────┘          │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
ai-devops-autopilot/
├── 📄 src/                          # Main source code
│   ├── main.py                      # FastAPI app entry point (154KB)
│   ├── auth.py                      # Authentication (JWT, sessions, bcrypt)
│   ├── database.py                  # PostgreSQL connection/ORM
│   ├── models.py                    # SQLAlchemy models (User, Subscription, etc.)
│   ├── autonomous_executor.py       # Phase 3 autonomous remediation
│   ├── worker.py                    # Background event processor
│   ├── worker_phase2.py             # Enhanced worker with learning
│   ├── worker_phase3.py             # Autonomous execution worker
│   │
│   ├── 📂 api/                      # API Routers
│   │   ├── auth_api.py              # Auth endpoints (/register, /login, /me)
│   │   ├── subscription_api.py      # Subscription management
│   │   ├── dashboard_api.py         # Dashboard data endpoints
│   │   ├── razorpay_api.py          # Payment gateway integration
│   │   ├── suppression_api.py       # Alert suppression rules
│   │   ├── slack_notifier.py        # Slack alert formatting
│   │   └── slack_interactive.py     # Slack button callbacks
│   │
│   ├── 📂 actions/                  # Remediation Actions (6 files)
│   │   ├── action_library.py        # 50+ predefined actions
│   │   ├── runbook_actions.py       # Runbook integration
│   │   └── ...
│   │
│   ├── 📂 alerts/                   # Alert Processing (2 files)
│   │   ├── noise_suppressor.py      # Dedup, flapping, suppression
│   │   └── __init__.py
│   │
│   ├── 📂 analytics/                # Metrics & Analysis (4 files)
│   │   ├── action_recorder.py       # Track action outcomes
│   │   └── ...
│   │
│   ├── 📂 cloud_costs/              # Cloud Cost Optimization (6 files)
│   │   ├── aws_integration.py       # AWS Cost Explorer
│   │   ├── gcp_integration.py       # GCP Billing
│   │   ├── azure_integration.py     # Azure Cost Management
│   │   └── encryption.py            # Credential encryption
│   │
│   ├── 📂 decision/                 # Decision Engine (2 files)
│   │   ├── cross_tool_layer.py      # Multi-tool orchestration
│   │   └── __init__.py
│   │
│   ├── 📂 detection/                # Anomaly Detection (2 files)
│   │   ├── anomaly_detector.py      # Statistical detection
│   │   └── ai_analyzer.py           # AI-powered analysis
│   │
│   ├── 📂 learning/                 # ML & Learning (2 files)
│   │   ├── learning_engine.py       # Pattern learning
│   │   └── __init__.py
│   │
│   ├── 📂 llm/                      # LLM Integration (2 files)
│   │   ├── llm_adapter.py           # Ollama/OpenAI adapter
│   │   └── __init__.py
│   │
│   ├── 📂 runbooks/                 # Automation Runbooks (2 files)
│   │   ├── runbook_engine.py        # YAML runbook executor
│   │   └── __init__.py
│   │
│   ├── 📂 training/                 # DevOps Knowledge (9 files)
│   │   ├── devops_knowledge_base.py # Training patterns
│   │   ├── patterns_*.py            # Pattern libraries
│   │   └── ...
│   │
│   ├── 📂 notifications/            # Email & Notifications
│   │   └── email.py                 # SendGrid integration
│   │
│   └── 📂 scheduler/                # Background Jobs
│       └── trial_jobs.py            # Trial/subscription jobs
│
├── 📄 Deployr_dashboard.html        # Main SPA Dashboard (337KB)
├── 📄 requirements.txt              # Python dependencies
├── 📄 Dockerfile                    # Container definition
├── 📄 docker-compose.yml            # Multi-service orchestration
├── 📄 .env                          # Environment variables
├── 📄 prometheus.yml                # Prometheus config
│
├── 📂 tests/                        # Test files
├── 📂 docs/                         # Documentation
├── 📂 infra/                        # Infrastructure configs
└── 📂 img/                          # Dashboard images
```

---

## 🔄 Data Flow Diagrams

### 1. User Authentication Flow
```
┌─────────┐     POST /api/auth/login      ┌─────────┐
│ Browser │ ────────────────────────────▶ │  API    │
│         │     {email, password}         │         │
└─────────┘                               └────┬────┘
                                               │
                                               ▼
                                     ┌─────────────────┐
                                     │  auth_api.py    │
                                     │  - Validate creds│
                                     │  - bcrypt verify │
                                     └────────┬────────┘
                                              │
                                              ▼
                                     ┌─────────────────┐
                                     │   PostgreSQL    │
                                     │  users table    │
                                     └────────┬────────┘
                                              │
                                              ▼
                                     ┌─────────────────┐
                                     │ Generate JWT    │
                                     │ Create session  │
                                     └────────┬────────┘
                                              │
                                              ▼
┌─────────┐     {access_token, user}  ┌─────────────────┐
│ Browser │ ◀──────────────────────── │  Store token    │
│         │                           │  in localStorage│
└─────────┘                           └─────────────────┘
```

### 2. Incident Detection & Alert Flow
```
┌────────────────┐
│ Data Sources   │
│ • Prometheus   │
│ • App Logs     │
│ • K8s Events   │
└───────┬────────┘
        │
        ▼ POST /ingest/*
┌──────────────────┐
│   FastAPI        │
│   Ingestion      │
└───────┬──────────┘
        │
        ▼ Store
┌──────────────────┐
│   Redis          │
│   Event Stream   │
└───────┬──────────┘
        │
        ▼ Poll
┌──────────────────┐      ┌──────────────────┐
│   Worker         │─────▶│ Anomaly Detector │
│   Background     │      │ - Z-score calc   │
└───────┬──────────┘      │ - Threshold check│
        │                 └──────────────────┘
        │
        ▼ If Anomaly Detected
┌──────────────────┐      ┌──────────────────┐
│ Noise Suppressor │─────▶│ Check:           │
│ - Deduplication  │      │ - Duplicate?     │
│ - Flapping check │      │ - Flapping?      │
│ - Actionability  │      │ - Maintenance?   │
└───────┬──────────┘      └──────────────────┘
        │
        ▼ If Not Suppressed
┌──────────────────┐      ┌──────────────────┐
│   AI Analyzer    │─────▶│   Ollama LLM     │
│   (llama3)       │      │ - Root cause     │
│                  │      │ - Recommended    │
│                  │      │   actions        │
└───────┬──────────┘      └──────────────────┘
        │
        ├──────────────────────────────────┐
        ▼                                  ▼
┌──────────────────┐              ┌──────────────────┐
│  Slack Notifier  │              │  Dashboard       │
│  - Rich alerts   │              │  - Live update   │
│  - Action buttons│              │  - Incident view │
└──────────────────┘              └──────────────────┘
```

### 3. Autonomous Remediation Flow
```
┌──────────────────┐
│ Incident Created │
└───────┬──────────┘
        │
        ▼
┌──────────────────┐     ┌──────────────────┐
│ Check Mode       │────▶│ Manual/Supervised│───▶ Wait for approval
│                  │     │ /Autonomous      │
└───────┬──────────┘     └──────────────────┘
        │
        ▼ Autonomous Mode
┌──────────────────┐
│ Safety Rails     │
│ - Confidence >80%│
│ - Risk = low     │
│ - In hours?      │
└───────┬──────────┘
        │
        ├─────────────────────────────────────┐
        │ Safe                                │ Unsafe
        ▼                                     ▼
┌──────────────────┐              ┌──────────────────┐
│ Auto Execute     │              │ Escalate to      │
│ - Run action     │              │ Human            │
│ - Record outcome │              │ - Slack notify   │
│ - Learn pattern  │              │ - Pending action │
└──────────────────┘              └──────────────────┘
```

---

## 🔌 API Endpoints Summary

### Authentication (`/api/auth/*`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Create new user + trial |
| POST | `/login` | Authenticate, get JWT |
| POST | `/logout` | Invalidate session |
| GET | `/me` | Get current user profile |
| POST | `/refresh` | Refresh access token |
| POST | `/password-reset` | Request password reset |
| POST | `/password-reset/confirm` | Set new password |

### Subscription (`/api/subscription/*`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/plans` | List available plans |
| GET | `/current` | Get user's subscription |
| POST | `/upgrade` | Change subscription plan |
| GET | `/usage` | Get feature usage stats |

### Dashboard (`/api/dashboard/*`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/stats` | Dashboard statistics |
| GET | `/incidents` | List incidents |
| GET | `/actions` | List pending actions |
| POST | `/action/approve` | Approve pending action |
| POST | `/action/reject` | Reject pending action |
| POST | `/incident/{id}/resolve` | Resolve incident |

### Suppression Rules (`/api/suppression/*`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/rules` | Get user's suppression rules |
| PUT | `/rules/{id}` | Update rule configuration |
| POST | `/rules/{id}/toggle` | Enable/disable rule |

---

## 💾 Database Schema

### PostgreSQL Tables
```sql
-- Users table
users (
    user_id: UUID PRIMARY KEY,
    email: VARCHAR UNIQUE NOT NULL,
    hashed_password: VARCHAR NOT NULL,
    full_name: VARCHAR,
    company: VARCHAR,
    is_active: BOOLEAN DEFAULT TRUE,
    is_superuser: BOOLEAN DEFAULT FALSE,
    email_verified: BOOLEAN DEFAULT FALSE,
    created_at: TIMESTAMP,
    updated_at: TIMESTAMP
)

-- Subscriptions table
subscriptions (
    subscription_id: UUID PRIMARY KEY,
    user_id: UUID FOREIGN KEY -> users,
    plan: ENUM (free, trial, pro, enterprise),
    status: ENUM (trialing, active, expired, cancelled),
    trial_end: TIMESTAMP,
    current_period_end: TIMESTAMP,
    razorpay_subscription_id: VARCHAR,
    feature_limits: JSON,
    created_at: TIMESTAMP
)

-- API Keys table
api_keys (
    key_id: UUID PRIMARY KEY,
    user_id: UUID FOREIGN KEY -> users,
    key_hash: VARCHAR NOT NULL,
    name: VARCHAR,
    permissions: JSON,
    is_active: BOOLEAN DEFAULT TRUE,
    last_used: TIMESTAMP,
    created_at: TIMESTAMP
)

-- Sessions table
sessions (
    session_id: UUID PRIMARY KEY,
    user_id: UUID FOREIGN KEY -> users,
    token_hash: VARCHAR NOT NULL,
    ip_address: VARCHAR,
    user_agent: VARCHAR,
    is_active: BOOLEAN DEFAULT TRUE,
    expires_at: TIMESTAMP,
    created_at: TIMESTAMP
)
```

### Redis Data Structures
```
# Event Streams
events:metrics:{service}     - Metric data points
events:logs:{service}        - Log entries
events:deployments:{service} - Deployment events

# Baselines (Hashes)
baseline:{service}:{metric}  - Mean, std_dev, count

# Incidents (Lists)
incidents:{service}          - Recent incidents
recent_anomalies:{service}   - Last 100 anomalies

# Sessions
session:{session_id}         - Session data (TTL)

# Rate Limiting
rate:{ip}:{endpoint}         - Request counts
```

---

## 🧪 Testing Strategy

### Unit Tests
```bash
pytest tests/unit/ -v
# Test individual functions:
# - auth.py: password hashing, JWT generation
# - anomaly_detector.py: z-score calculation
# - noise_suppressor.py: dedup, flapping detection
```

### Integration Tests
```bash
pytest tests/integration/ -v
# Test component interactions:
# - API endpoints with database
# - Redis event processing
# - Slack webhook delivery
```

### End-to-End Tests
```bash
pytest tests/e2e/ -v
# Full flows:
# - User signup → login → subscription
# - Metric ingest → anomaly → alert
# - Autonomous action execution
```

### Load Tests
```bash
locust -f tests/load/locustfile.py
# Metrics:
# - 1000 requests/second
# - Concurrent users: 100
# - Response time < 100ms (p95)
```

---

## 🚀 Running Locally

### Development Mode
```bash
# 1. Start dependencies
docker-compose up -d postgres redis ollama

# 2. Initialize database
python init_database.py

# 3. Start API
uvicorn src.main:app --reload --port 8000

# 4. Start worker (separate terminal)
python src/worker.py

# 5. Open dashboard
# file:///path/to/Deployr_dashboard.html
```

### Full Stack (Docker)
```bash
docker-compose up --build
# Access:
# - API: http://localhost:8000
# - pgAdmin: http://localhost:5050
# - Ollama: http://localhost:11434
```

---

## 📊 Environment Variables

```bash
# Required
DATABASE_URL=postgresql://deployr:password@localhost:5432/deployr
REDIS_URL=redis://localhost:6379
JWT_SECRET_KEY=your-secret-key-here

# Optional
ANTHROPIC_API_KEY=...          # If using Claude
OPENAI_API_KEY=...             # If using GPT
OLLAMA_BASE_URL=http://localhost:11434
SLACK_WEBHOOK_URL=...          # For alerts
RAZORPAY_KEY_ID=...            # Payment gateway
RAZORPAY_KEY_SECRET=...
SENDGRID_API_KEY=...           # Email notifications

# Security
ALLOWED_ORIGINS=http://localhost:8000,file://
ALLOWED_HOSTS=localhost,127.0.0.1
```

---

## 📝 Reminder for Deployment

> **TODO**: Implement Google OAuth for profile pictures
> - Need: Google Cloud Client ID
> - Will fetch actual Google profile photo
> - Deferred until production deployment

---

*Last Updated: January 2026*
*Version: 0.3.0*
