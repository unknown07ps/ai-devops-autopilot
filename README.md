#  AI DevOps Autopilot

**An autonomous SRE that detects, diagnoses, fixes, and explains production incidents — with minimal human intervention.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com/)
[![Redis](https://img.shields.io/badge/Redis-7.0+-red.svg)](https://redis.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

##  What Does It Do?

**Stop chasing alerts. Let AI handle incidents.**

AI DevOps Autopilot watches your production systems 24/7 and:

1. **Detects** anomalies in metrics (latency spikes, error rates, etc.)
2. **Correlates** signals across logs, metrics, and deployments
3. **Analyzes** root cause using AI reasoning (local LLM)
4. **Alerts** your team on Slack with actionable insights
5. *(Coming Soon)* **Fixes** issues automatically with approval

**Example Alert:**

```
 CRITICAL Incident - auth-api
Detected: 2025-12-28 10:03:42 UTC
Confidence: 90%

Root Cause: Memory leak in v2.1.0 deployment
- API latency spiked from 108ms to 1500ms (+1284%)
- Error rate increased to 15% (baseline: 0.2%)
- Deployment correlation: 8 minutes ago

Recommended Actions:
1. Rollback to v2.0.9 (Risk: Low) ← Highest priority
2. Scale pods from 3 to 6 (Risk: Medium)
3. Investigate memory usage (Risk: None)

Customer Impact: 5000 users experiencing slow logins
```

---

##  Key Features

### **Phase 1: Detect + Explain (Current MVP)**
-  **Anomaly Detection** - Statistical Z-score with self-learning baselines
-  **AI Root Cause Analysis** - Uses local LLM (Ollama) for reasoning
-  **Slack Alerts** - Rich formatted incident reports
-  **Deployment Correlation** - Automatically links incidents to code changes
-  **Multi-Signal Analysis** - Combines metrics, logs, and events

### **Phase 2: Supervised Actions (Roadmap)**
-  Rollback recommendations with approval buttons
-  Auto-scaling suggestions
-  Service restart capabilities
-  Incident memory for learning

### **Phase 3: Autonomous Mode (Future)**
-  Night-mode auto-remediation
-  Confidence-based execution
-  Safe-guard rails
-  Action outcome learning

---

##  Quick Start (5 Minutes)

### **Prerequisites**
- Python 3.11+
- Docker Desktop
- [Ollama](https://ollama.com/) installed
- Slack workspace (free)

### **1. Clone & Setup**

```bash
git clone https://github.com/yourusername/ai-devops-autopilot.git
cd ai-devops-autopilot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### **2. Start Redis**

```bash
docker run -d -p 6379:6379 --name redis redis:7-alpine
```

### **3. Pull AI Model**

```bash
# For balanced performance (recommended)
ollama pull llama3:latest

# For faster inference
ollama pull llama3.2:3b
```

### **4. Configure Environment**

Create `.env` file:

```env
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3:latest

# Slack Webhook (get from https://api.slack.com/messaging/webhooks)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Redis
REDIS_URL=redis://localhost:6379

# Environment
ENVIRONMENT=development
```

### **5. Start Services**

**Terminal 1 - API:**
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Worker:**
```bash
python src/worker.py
```

**Terminal 3 - Test:**
```bash
python test_clean.py
```

**Check Slack!** You should receive an incident alert! 🎉

---

##  Architecture

```
Production → [Ingestion API] → [Redis] → [Worker]
                                            ↓
                            [Anomaly Detector] → [AI Analyzer]
                                            ↓
                                      [Slack Alert]
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system design.

---

##  Configuration

### **Anomaly Detection Tuning**

Edit `src/detection/anomaly_detector.py`:

```python
self.std_dev_threshold = 2.5  # Sensitivity (lower = more sensitive)
self.lookback_window = timedelta(minutes=15)  # Baseline window
```

### **AI Prompt Customization**

Edit `src/detection/ai_analyzer.py` to change analysis style.

### **Slack Alert Format**

Edit `src/api/slack_notifier.py` for custom formatting.

---

##  API Reference

### **Health Check**
```bash
GET /health
```

### **Ingest Metrics**
```bash
POST /ingest/metrics
Content-Type: application/json

[{
  "timestamp": "2025-12-28T10:00:00Z",
  "metric_name": "api_latency_ms",
  "value": 150.5,
  "labels": {
    "service": "auth-api",
    "environment": "production"
  }
}]
```

### **Ingest Logs**
```bash
POST /ingest/logs
Content-Type: application/json

[{
  "timestamp": "2025-12-28T10:00:00Z",
  "level": "ERROR",
  "message": "Database connection timeout",
  "service": "auth-api",
  "labels": {}
}]
```

### **Track Deployment**
```bash
POST /ingest/deployment
Content-Type: application/json

{
  "timestamp": "2025-12-28T09:55:00Z",
  "service": "auth-api",
  "version": "v2.1.0",
  "status": "success",
  "metadata": {
    "commit": "abc123"
  }
}
```

---

##  Testing

### **Unit Tests**
```bash
pytest tests/
```

### **End-to-End Test**
```bash
python test_clean.py
```

### **Load Test**
```bash
python test_load.py  # TODO: Create this
```

---

##  Docker Deployment

```bash
docker-compose up --build
```

See `docker-compose.yml` for configuration.

---

##  How It Works

### **1. Anomaly Detection Algorithm**

Uses **Z-score (Standard Deviation)** method:

```
Z = (current_value - mean) / std_dev

If Z > 2.5 → Anomaly!
```

**Why Z-score?**
-  No training data needed
-  Works immediately
-  Self-adjusting
-  Interpretable

**Baseline Learning:**
- Tracks last 1000 samples per metric
- Calculates rolling mean and std dev
- Requires 10 samples minimum
- Updates with each new data point

### **2. AI Root Cause Analysis**

**Input Context:**
- Detected anomalies with severity
- Recent error logs (last 10 min)
- Recent deployments (last 30 min)
- Service metadata

**Reasoning Process:**
1. LLM analyzes all signals
2. Identifies most likely cause
3. Ranks remediation actions
4. Assesses customer impact
5. Provides confidence score

**Why Local LLM (Ollama)?**
-  **Privacy** - Data never leaves your infrastructure
-  **Cost** - No API fees
-  **Speed** - No network latency
-  **Offline** - Works without internet

---

##  Real-World Use Cases

### **1. Deployment Rollback**
```
Scenario: New deployment causes 10x latency spike
Detection: 2 minutes after deploy
Action: Suggest rollback to previous version
Result: Issue resolved in 5 minutes vs 45 minutes manual
```

### **2. Database Overload**
```
Scenario: Connection pool exhausted
Detection: Error rate spike + slow queries
Action: Scale database connections + investigate query
Result: Prevent cascading failure
```

### **3. Memory Leak**
```
Scenario: Gradual memory increase over 2 hours
Detection: Anomaly in memory metrics
Action: Restart affected pods + schedule investigation
Result: Prevent OOM crash
```

---

##  Roadmap

### **Q1 2026: Phase 2 - Supervised Actions**
- [ ] Slack interactive buttons
- [ ] Rollback execution (with approval)
- [ ] Auto-scaling integration
- [ ] Action audit trail

### **Q2 2026: Phase 3 - Autonomous Mode**
- [ ] Night mode (auto-fix during off-hours)
- [ ] Confidence-based execution
- [ ] Learning from action outcomes
- [ ] Predictive incident prevention

### **Q3 2026: Enterprise Features**
- [ ] Multi-tenant support
- [ ] RBAC & SSO
- [ ] Compliance reporting
- [ ] Custom playbooks

---

##  Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### **Areas We Need Help:**
-  Documentation improvements
-  More test coverage
-  Bug fixes
-  Feature enhancements
-  Internationalization

---

##  License

MIT License - see [LICENSE](LICENSE) for details.

---

##  Acknowledgments

- **FastAPI** - Amazing web framework
- **Ollama** - Making local LLMs accessible
- **Redis** - The backbone of our event system
- **Slack** - For webhooks and great UX

---

##  Community

-  **Issues:** [GitHub Issues](https://github.com/unknown07ps/ai-devops-autopilot)
-  **Discussions:** [GitHub Discussions](https://github.com/unknown07ps/ai-devops-autopilot/discussions)

---

##  Support

-  Email: sagarprajapati1374@gmail.com


---

**Built with love for DevOps teams who want to sleep better at night.**

*Star this repo if you find it useful!*