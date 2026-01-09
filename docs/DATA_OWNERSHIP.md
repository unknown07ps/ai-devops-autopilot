# Data Ownership: Redis vs PostgreSQL

This document clarifies the ownership and responsibilities of the two data stores in the AI DevOps Autopilot system.

## Overview

| Store | Role | Data Lifetime | Authoritative |
|-------|------|--------------|---------------|
| **PostgreSQL** | Persistent store of record | Permanent | ✅ Yes |
| **Redis** | Transient cache and event bus | TTL-based | ❌ No |

---

## PostgreSQL (Authoritative Data)

PostgreSQL is the **source of truth** for all business-critical data:

### Tables
- `users` - User accounts and authentication
- `subscriptions` - Billing and feature access (CRITICAL)
- `sessions` - Active user sessions
- `services` - Monitored services configuration
- `incidents` - Historical incident records
- `actions` - Remediation action history
- `suppression_rules` - User alert rules

### Guarantees
- ACID transactions
- Durable persistence
- Point-in-time recovery
- Referential integrity

---

## Redis (Transient Data)

Redis is used for **ephemeral data** that can be reconstructed:

### Data Types

| Key Pattern | Purpose | TTL |
|-------------|---------|-----|
| `baseline:{service}:{metric}` | Statistical baselines | 24h |
| `recent_anomalies:{service}` | Detection window | 1h |
| `incidents:{service}` | Active incident cache | 24h |
| `action:{id}` | Pending action state | 24h |
| `actions:pending` | Action approval queue | None |
| `events:*` | Event streams | 1h |
| `rate_limit:*` | Rate limiting counters | 1min |

### Data Loss Impact
- Redis data loss is **recoverable** - baselines rebuild from new metrics
- Active incidents may lose real-time state but PostgreSQL has permanent record
- Action queue loss requires re-submission

---

## Hybrid Patterns

### Incidents
1. Real-time tracking in Redis (`incidents:{service}`)
2. Permanent storage in PostgreSQL (`incidents` table)
3. Redis is cache, PostgreSQL is authoritative

### Actions
1. Pending queue in Redis (`actions:pending`)
2. Executed actions written to PostgreSQL
3. Redis tracks workflow state, PostgreSQL tracks history

---

## Recovery Procedures

### Redis Restart
- Baselines: Auto-rebuild from incoming metrics (10 samples minimum)
- Pending actions: Check PostgreSQL for incomplete actions
- Rate limits: Reset (safe - just re-imposes limits)

### PostgreSQL Recovery
- Use backup/restore procedures
- All Redis data is ephemeral and does not aid recovery

---

## Best Practices

1. **Never assume Redis data is permanent** - always have PostgreSQL backup path
2. **Write critical data to PostgreSQL first** - Redis second
3. **Use TTLs on all Redis keys** - prevent unbounded growth
4. **Reconnect on Redis failure** - don't crash the application
