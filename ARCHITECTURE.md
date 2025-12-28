# AI DevOps Autopilot - System Architecture

##  High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRODUCTION ENVIRONMENT                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Prometheus   │  │ Application  │  │ Kubernetes   │          │
│  │   Metrics    │  │     Logs     │  │  Deployments │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                   │
│         └──────────────────┼──────────────────┘                  │
│                            │                                      │
└────────────────────────────┼──────────────────────────────────────┘
                             │
                    ┌────────▼─────────┐
                    │   INGESTION API  │
                    │   (FastAPI)      │
                    │   Port: 8000     │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   REDIS STORE    │
                    │   (Event Queue)  │
                    │   Port: 6379     │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ BACKGROUND WORKER│
                    │  (Event Processor)│
                    └────────┬─────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
     ┌──────▼──────┐  ┌─────▼─────┐  ┌──────▼──────┐
     │  ANOMALY    │  │    AI     │  │   SLACK     │
     │  DETECTOR   │  │ ANALYZER  │  │  NOTIFIER   │
     │             │  │ (Ollama)  │  │             │
     └─────────────┘  └───────────┘  └─────────────┘
```

---

##  Core Components

### **1. Ingestion API (`src/main.py`)**
**Purpose:** Entry point for all observability data

**Endpoints:**
- `GET /health` - Health check
- `POST /ingest/metrics` - Accept Prometheus-compatible metrics
- `POST /ingest/logs` - Accept application logs
- `POST /ingest/deployment` - Track deployment events

**Technology:** FastAPI + Pydantic for validation

**Flow:**
1. Validates incoming data
2. Stores in Redis for processing
3. Triggers background tasks
4. Returns 200 OK immediately (non-blocking)

---

### **2. Redis Event Store**
**Purpose:** Central event streaming and state management

**Data Structures:**
- **Streams** (if available): `events:metrics`, `events:logs`, `events:deployments`
- **Sorted Sets**: `deployments:{service}` - Deployment timeline
- **Hashes**: `baseline:{service}:{metric}` - Statistical baselines
- **Lists**: `recent_anomalies:{service}` - Last 100 anomalies
- **Lists**: `incidents:{service}` - Historical incidents

**Why Redis?**
- Fast in-memory processing
- Pub/Sub for real-time events
- Persistence for baselines
- Scalable to multiple workers

---

### **3. Background Worker (`src/worker.py`)**
**Purpose:** Async event processing and incident correlation

**Responsibilities:**
- Poll Redis for new metrics/logs
- Detect anomalies in real-time
- Correlate signals across sources
- Trigger AI analysis
- Send alerts

**Architecture Pattern:** Event-driven with async/await

**Processing Loop:**
```python
while True:
    1. Read new events from Redis
    2. Check for anomalies
    3. Correlate with deployments
    4. If threshold met → Trigger incident analysis
    5. Sleep and repeat
```

---

### **4. Anomaly Detector (`src/detection/anomaly_detector.py`)**
**Purpose:** Statistical anomaly detection with self-learning

**Algorithm:**
- **Method:** Z-score (Standard Deviation)
- **Threshold:** 2.5 standard deviations
- **Baseline:** Rolling window of last 1000 samples
- **Cold Start:** Requires 10 samples before detection

**How it works:**
```
Z-score = (current_value - mean) / std_dev

If Z > 2.5:
  - Severity: critical (Z > 4)
  - Severity: high (Z > 3)
  - Severity: medium (Z > 2.5)
```

**Features:**
- Auto-learning baselines
- Per-service, per-metric tracking
- Deployment correlation
- Error rate spike detection

---

### **5. AI Analyzer (`src/detection/ai_analyzer.py`)**
**Purpose:** Root cause analysis using LLM reasoning

**Model:** Ollama (local inference)
- Default: `llama3:latest` (8B parameters)
- Alternative: `llama3.2:3b` (faster)

**Input Context:**
- Detected anomalies with Z-scores
- Recent error logs (last 10 min)
- Recent deployments (last 30 min)
- Service metadata

**Output (JSON):**
```json
{
  "root_cause": {
    "description": "...",
    "confidence": 85,
    "reasoning": "..."
  },
  "recommended_actions": [
    {
      "action": "rollback deployment",
      "reasoning": "...",
      "risk": "low",
      "priority": 1
    }
  ],
  "severity": "high",
  "estimated_customer_impact": "..."
}
```

**Fallback:** If AI times out, uses rule-based analysis

---

### **6. Slack Notifier (`src/api/slack_notifier.py`)**
**Purpose:** Rich incident alerts to Slack

**Features:**
- Color-coded by severity
- Anomaly breakdown
- Recommended actions
- Customer impact assessment

**Alert Format:**
- Header with emoji and severity
- Root cause summary
- Anomaly details with metrics
- Action recommendations with risk levels
- Estimated customer impact

---

##  Data Flow - End to End

### **Normal Metric Flow:**
```
1. Prometheus scrapes metric → 100ms latency
2. POST /ingest/metrics
3. Store in Redis
4. Worker detects: within baseline
5. Update rolling average
6. No alert
```

### **Anomaly Detection Flow:**
```
1. Deployment happens at 10:00 AM
2. POST /ingest/deployment
3. Store in Redis sorted set

4. New metrics arrive → 1500ms latency
5. POST /ingest/metrics
6. Store in Redis

7. Worker polls Redis
8. Detector calculates Z-score = 242 (!!!)
9. Classify as CRITICAL anomaly
10. Store anomaly for correlation

11. Error logs arrive
12. POST /ingest/logs
13. Worker detects error spike

14. Correlation Engine:
    - 2 anomalies detected
    - Error rate spike
    - Recent deployment 8 min ago
    → TRIGGER INCIDENT

15. AI Analyzer:
    - Build context (anomalies + logs + deployment)
    - Call Ollama with prompt
    - Parse JSON response
    - Generate analysis

16. Slack Notifier:
    - Format rich message
    - Send via webhook
    - Log result

17. Store incident in Redis for learning
```

---

##  Data Models

### **MetricPoint**
```python
{
  "timestamp": "2025-12-28T10:00:00Z",
  "metric_name": "api_latency_ms",
  "value": 1500.0,
  "labels": {
    "service": "auth-api",
    "environment": "production"
  }
}
```

### **LogEntry**
```python
{
  "timestamp": "2025-12-28T10:00:00Z",
  "level": "ERROR",
  "message": "Database timeout",
  "service": "auth-api",
  "labels": {
    "component": "database"
  }
}
```

### **DeploymentEvent**
```python
{
  "timestamp": "2025-12-28T09:55:00Z",
  "service": "auth-api",
  "version": "v2.1.0",
  "status": "success",
  "metadata": {
    "commit": "abc123",
    "deployed_by": "ci-cd"
  }
}
```

### **Anomaly**
```python
{
  "metric_name": "api_latency_ms",
  "service": "auth-api",
  "current_value": 1500.0,
  "baseline_mean": 108.0,
  "baseline_std_dev": 5.74,
  "z_score": 242.29,
  "deviation_percent": 1284.0,
  "severity": "critical",
  "detected_at": "2025-12-28T10:00:00Z"
}
```

---

##  Security Considerations

### **Current State (MVP):**
-  No authentication on API
-  No rate limiting
-  Webhook URL in plaintext

### **Production Requirements:**
-  API key authentication
-  Rate limiting per client
-  Secrets management (Vault/AWS Secrets)
-  TLS/HTTPS only
-  Input validation (already implemented)
-  SQL injection prevention (no SQL used)

---

##  Scalability

### **Current Capacity:**
- **Single worker:** ~10,000 metrics/min
- **Redis:** ~50,000 ops/sec
- **Bottleneck:** AI inference (30-60s per incident)

### **Scaling Strategy:**

**Horizontal Scaling:**
1. Multiple workers reading from same Redis
2. Load balancer in front of API
3. Redis Cluster for high availability

**Vertical Scaling:**
1. GPU for Ollama (10x faster inference)
2. Larger Redis instance
3. More worker threads

**Optimization:**
1. Batch metric processing
2. Async AI calls
3. Cache frequent patterns

---

##  Testing Strategy

### **Unit Tests:**
- Anomaly detection logic
- Baseline calculation
- Z-score computation

### **Integration Tests:**
- API endpoints
- Redis storage
- Slack webhook

### **End-to-End Tests:**
- Full incident flow
- AI analysis
- Alert delivery

### **Load Tests:**
- 1000 metrics/sec
- Concurrent incidents
- Worker recovery

---

##  Deployment Options

### **Option 1: Docker Compose (Current)**
```yaml
services:
  - redis
  - api
  - worker
```

### **Option 2: Kubernetes**
```yaml
Deployments:
  - api (3 replicas)
  - worker (5 replicas)
StatefulSets:
  - redis (1 primary + 2 replicas)
Services:
  - api-loadbalancer
  - redis-service
```

### **Option 3: Cloud Native**
- **API:** AWS Lambda / Cloud Run
- **Redis:** ElastiCache / Redis Cloud
- **Worker:** ECS Fargate / Cloud Run Jobs
- **AI:** SageMaker / Vertex AI

---

##  Future Enhancements (Roadmap)

### **Phase 2: Supervised Actions**
- Rollback with approval button
- Scale pods automatically
- Restart services
- Kill noisy neighbors

### **Phase 3: Autonomous Mode**
- Night mode auto-remediation
- Confidence-based execution
- Action learning from outcomes

### **Phase 4: Advanced Analytics**
- Predictive incident detection
- Capacity planning
- Cost optimization
- Cross-service correlation

### **Phase 5: Enterprise**
- Multi-tenant
- RBAC
- SSO
- Audit trails
- Compliance reports

---

##  Technology Stack

| Component | Technology | Why? |
|-----------|-----------|------|
| API | FastAPI | Fast, async, auto-docs |
| Validation | Pydantic | Type safety, validation |
| Storage | Redis | Speed, pub/sub, persistence |
| AI | Ollama | Local, private, free |
| Alerts | Slack | Universal, rich formatting |
| Language | Python 3.11+ | Rapid development, ML ecosystem |
| Container | Docker | Portability, consistency |

---

##  Key Design Decisions

### **Why Redis over Kafka?**
- Simpler setup
- Built-in persistence
- Sufficient for MVP scale
- Can migrate to Kafka later

### **Why Ollama over OpenAI?**
- No API costs
- Data privacy
- No rate limits
- Works offline

### **Why Statistical Detection over ML?**
- No training data needed
- Instant deployment
- Interpretable results
- Good enough for 80% of cases

### **Why Slack over PagerDuty?**
- Simpler integration
- Lower cost
- Rich formatting
- Where teams already are

---

##  Best Practices Implemented

1. **Async Everything** - Non-blocking I/O
2. **Fail Gracefully** - Fallbacks everywhere
3. **Log Abundantly** - Debug-friendly
4. **Type Strictly** - Pydantic models
5. **Document Clearly** - Self-documenting code
6. **Test Thoroughly** - Test scripts included
7. **Deploy Simply** - Docker Compose ready

---

##  Known Limitations

1. **Redis Streams** - Fallback needed for older Redis
2. **AI Timeout** - Large models can be slow
3. **No Authentication** - MVP only
4. **Single Worker** - Not HA yet
5. **Memory Baselines** - Lost on restart (mitigated by Redis persistence)

---

##  Support & Contribution

- **Issues:** Report bugs on GitHub
- **PRs:** Contributions welcome
- **Docs:** Keep this updated
- **Questions:** Create discussions

---

*Last Updated: December 2025*
*Version: 0.1.0 (MVP)*