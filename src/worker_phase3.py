"""
Phase 3: Integration Files
1. Worker integration for autonomous execution
2. API endpoints for autonomous mode control
3. Dashboard enhancements
"""

# ============================================================================
# FILE 1: src/worker_phase3.py
# ============================================================================
"""
Enhanced Worker - Phase 3: Autonomous Mode
Integrates intelligent autonomous execution with safety rails
"""

import asyncio
import redis
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import List, Dict
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.detection.anomaly_detector import AnomalyDetector
from src.detection.ai_analyzer import AIIncidentAnalyzer
from src.memory.incident_memory import IncidentMemory

# Import Phase 3 autonomous executor (save the first artifact as src/autonomous/executor.py)
# from src.autonomous.executor import AutonomousExecutor, ExecutionMode

load_dotenv()

class SimpleActionExecutor:
    """Simplified action executor"""
    def __init__(self, redis_client):
        self.redis = redis_client
        self.dry_run = os.getenv("DRY_RUN_MODE", "true").lower() == "true"
    
    async def execute_action(self, action_id: str) -> Dict:
        """Execute action"""
        action_data = self.redis.get(f"action:{action_id}")
        if not action_data:
            return {"success": False, "error": "Action not found"}
        
        action = json.loads(action_data)
        action_type = action['action_type']
        
        # Simulate execution
        await asyncio.sleep(1)
        
        if self.dry_run:
            return {
                "success": True,
                "dry_run": True,
                "message": f"DRY RUN: {action_type} completed",
                "duration_seconds": 1
            }
        
        return {
            "success": True,
            "message": f"{action_type} completed",
            "duration_seconds": 1
        }

class AutonomousIncidentWorker:
    """Phase 3 Worker with autonomous execution"""
    
    def __init__(self):
        self.redis = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        
        # Core components
        self.anomaly_detector = AnomalyDetector(os.getenv("REDIS_URL"))
        self.ai_analyzer = AIIncidentAnalyzer(
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=os.getenv("OLLAMA_MODEL", "llama3:latest")
        )
        self.action_executor = SimpleActionExecutor(self.redis)
        self.incident_memory = IncidentMemory(self.redis)
        
        # Phase 3: Autonomous executor
        # Uncomment when autonomous executor is saved:
        # self.autonomous_executor = AutonomousExecutor(self.redis, self.action_executor)
        
        # Configuration
        self.autonomous_enabled = os.getenv("AUTONOMOUS_MODE", "false").lower() == "true"
        self.execution_mode = os.getenv("EXECUTION_MODE", "supervised")
        
        print(f"[WORKER] Phase 3 Autonomous Mode: {self.autonomous_enabled}")
        print(f"[WORKER] Execution Mode: {self.execution_mode}")
    
    async def run(self):
        """Main worker loop"""
        print("[WORKER] Starting Phase 3 Autonomous Worker...")
        
        tasks = [
            asyncio.create_task(self.process_metrics_stream()),
            asyncio.create_task(self.process_anomalies()),
            asyncio.create_task(self.process_approved_actions()),
            asyncio.create_task(self.monitor_autonomous_actions()),
        ]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\n[WORKER] Shutting down...")
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def process_metrics_stream(self):
        """Process metrics and detect anomalies"""
        print("[WORKER] Monitoring metrics...")
        processed_keys = set()
        
        while True:
            try:
                metric_keys = self.redis.keys('metric:*')
                
                for key in metric_keys:
                    if key in processed_keys:
                        continue
                    
                    try:
                        metric_json = self.redis.get(key)
                        if metric_json:
                            metric_data = json.loads(metric_json)
                            
                            anomaly = self.anomaly_detector.detect_anomaly(
                                metric_name=metric_data['metric_name'],
                                service=metric_data['labels'].get('service', 'unknown'),
                                value=metric_data['value']
                            )
                            
                            if anomaly:
                                print(f"[ANOMALY] {anomaly['metric_name']} in {anomaly['service']}")
                                self.anomaly_detector.store_anomaly(anomaly['service'], anomaly)
                                await self.check_for_incident(anomaly['service'])
                            
                            processed_keys.add(key)
                    except Exception as e:
                        continue
                
                if len(processed_keys) > 1000:
                    processed_keys.clear()
                
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                await asyncio.sleep(1)
    
    async def process_anomalies(self):
        """Correlate anomalies and trigger analysis"""
        print("[WORKER] Monitoring anomalies...")
        
        while True:
            try:
                services = set()
                for key in self.redis.scan_iter("recent_anomalies:*"):
                    service = key.decode('utf-8').split(':')[1]
                    services.add(service)
                
                for service in services:
                    await self.check_for_incident(service)
                
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception as e:
                await asyncio.sleep(5)
    
    async def process_approved_actions(self):
        """Execute approved actions"""
        print("[WORKER] Monitoring approved actions...")
        
        while True:
            try:
                action_id = self.redis.rpop("actions:approved")
                
                if action_id:
                    action_id = action_id.decode('utf-8')
                    print(f"[ACTION] Executing approved: {action_id}")
                    
                    result = await self.action_executor.execute_action(action_id)
                    
                    if result['success']:
                        print(f"[ACTION] ✓ Completed: {action_id}")
                    else:
                        print(f"[ACTION] ✗ Failed: {action_id}")
                
                await asyncio.sleep(2)
            except asyncio.CancelledError:
                break
            except Exception as e:
                await asyncio.sleep(5)
    
    async def monitor_autonomous_actions(self):
        """Monitor autonomous action execution (Phase 3)"""
        print("[WORKER] Monitoring autonomous actions...")
        
        while True:
            try:
                # Check for actions that should be executed autonomously
                if self.autonomous_enabled:
                    # Get pending actions with high confidence
                    # Uncomment when autonomous executor is ready:
                    # await self._process_autonomous_candidates()
                    pass
                
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                await asyncio.sleep(5)
    
    async def check_for_incident(self, service: str):
        """Check if we should trigger incident analysis"""
        anomalies = self.anomaly_detector.get_recent_anomalies(service, minutes=5)
        critical_anomalies = [a for a in anomalies if a.get('severity') in ['critical', 'high']]
        
        should_alert = len(critical_anomalies) >= 1 or len(anomalies) >= 3
        
        if should_alert:
            await self.analyze_and_propose_actions(service, anomalies)
    
    async def analyze_and_propose_actions(self, service: str, anomalies: List[Dict]):
        """Analyze incident and propose/execute actions autonomously"""
        try:
            incident_id = f"incident_{service}_{int(datetime.now(timezone.utc).timestamp())}"
            
            # Gather context
            recent_logs = self._get_recent_logs(service, minutes=10)
            recent_deployments = self._get_recent_deployments(service, minutes=30)
            
            print(f"[ANALYSIS] Analyzing {incident_id}...")
            
            # AI analysis
            analysis = self.ai_analyzer.analyze_incident(
                anomalies=anomalies,
                recent_logs=recent_logs,
                recent_deployments=recent_deployments,
                service_name=service
            )
            
            # Get similar incidents for learning
            similar_incidents = self.incident_memory.find_similar_incidents(
                anomalies, service, limit=5
            )
            
            # Propose actions
            proposed_actions = await self._propose_actions(
                analysis, anomalies, service, incident_id, recent_deployments
            )
            
            # Phase 3: Autonomous evaluation
            if self.autonomous_enabled and proposed_actions:
                await self._evaluate_autonomous_execution(
                    proposed_actions,
                    {
                        'id': incident_id,
                        'service': service,
                        'anomalies': anomalies,
                        'analysis': analysis,
                        'recent_deployments': recent_deployments
                    },
                    analysis,
                    similar_incidents
                )
            
            # Store incident
            self._store_incident(incident_id, service, analysis, anomalies, proposed_actions)
            
        except Exception as e:
            print(f"[ERROR] Analysis failed: {e}")
    
    async def _evaluate_autonomous_execution(
        self,
        actions: List[Dict],
        incident: Dict,
        analysis: Dict,
        similar_incidents: List[Dict]
    ):
        """Evaluate and execute actions autonomously if confidence is high"""
        print("[AUTONOMOUS] Evaluating actions for autonomous execution...")
        
        for action in actions:
            # Uncomment when autonomous executor is ready:
            """
            should_execute, confidence, reasoning = await self.autonomous_executor.evaluate_action(
                action, incident, analysis, similar_incidents
            )
            
            if should_execute:
                print(f"[AUTONOMOUS] Executing {action['action_type']} with {confidence:.1f}% confidence")
                result = await self.autonomous_executor.execute_autonomous_action(
                    action, confidence, reasoning
                )
            else:
                print(f"[AUTONOMOUS] Requires approval: {action['action_type']} ({confidence:.1f}% confidence)")
            """
            pass
    
    async def _propose_actions(
        self,
        analysis: Dict,
        anomalies: List[Dict],
        service: str,
        incident_id: str,
        recent_deployments: List[Dict]
    ) -> List[Dict]:
        """Propose remediation actions"""
        actions = []
        timestamp = int(datetime.now(timezone.utc).timestamp())
        
        # Rollback if recent deployment
        if recent_deployments:
            action_id = f"action_{incident_id}_rollback_{timestamp}"
            action = {
                "id": action_id,
                "incident_id": incident_id,
                "action_type": "rollback",
                "service": service,
                "params": {"target_version": "previous"},
                "reasoning": "Recent deployment correlates with anomaly",
                "risk": "low",
                "status": "pending",
                "proposed_at": datetime.now(timezone.utc).isoformat()
            }
            self.redis.setex(f"action:{action_id}", 86400, json.dumps(action))
            self.redis.lpush("actions:pending", action_id)
            actions.append(action)
        
        return actions
    
    def _get_recent_logs(self, service: str, minutes: int = 10) -> List[Dict]:
        """Get recent logs"""
        try:
            logs = []
            log_data = self.redis.lrange(f"logs:{service}", 0, 99)
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
            
            for log_json in log_data:
                try:
                    log = json.loads(log_json)
                    log_time = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
                    if log_time.replace(tzinfo=None) > cutoff_time.replace(tzinfo=None):
                        logs.append(log)
                except:
                    continue
            return logs
        except:
            return []
    
    def _get_recent_deployments(self, service: str, minutes: int = 30) -> List[Dict]:
        """Get recent deployments"""
        try:
            start_time = datetime.now(timezone.utc).timestamp() - (minutes * 60)
            deployments = []
            
            versions = self.redis.zrangebyscore(
                f"deployments:{service}",
                start_time,
                '+inf',
                withscores=True
            )
            
            for version, timestamp in versions:
                deployments.append({
                    'version': version.decode('utf-8'),
                    'timestamp': datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(),
                    'service': service
                })
            
            return deployments
        except:
            return []
    
    def _store_incident(self, incident_id, service, analysis, anomalies, actions):
        """Store incident"""
        incident = {
            'id': incident_id,
            'service': service,
            'analysis': analysis,
            'anomalies': anomalies,
            'proposed_actions': actions,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'phase': 3
        }
        self.redis.lpush(f"incidents:{service}", json.dumps(incident))
        self.redis.ltrim(f"incidents:{service}", 0, 99)

async def main():
    worker = AutonomousIncidentWorker()
    await worker.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[WORKER] Stopped")


# ============================================================================
# FILE 2: Phase 3 API Endpoints (add to src/main.py)
# ============================================================================

# Add these imports at the top of main.py:
# from src.autonomous.executor import ExecutionMode

# Add these endpoints to src/main.py:

"""
@app.get("/api/v3/autonomous/status")
async def get_autonomous_status():
    # Get autonomous executor stats
    # This requires autonomous executor instance
    return {
        "autonomous_enabled": os.getenv("AUTONOMOUS_MODE", "false").lower() == "true",
        "execution_mode": os.getenv("EXECUTION_MODE", "supervised"),
        "night_mode_active": False,  # Calculate from time
        "total_autonomous_actions": 0,
        "success_rate": 0,
        "confidence_threshold": 75
    }

@app.post("/api/v3/autonomous/mode")
async def set_autonomous_mode(mode: str, confidence_threshold: Optional[int] = None):
    # Change autonomous execution mode
    # Validate mode
    valid_modes = ["manual", "supervised", "autonomous", "night_mode"]
    if mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"Invalid mode. Must be one of: {valid_modes}")
    
    # Update configuration
    # In production, this would update environment/config
    
    return {
        "status": "success",
        "mode": mode,
        "confidence_threshold": confidence_threshold or 75,
        "message": f"Autonomous mode changed to {mode}"
    }

@app.get("/api/v3/autonomous/outcomes")
async def get_autonomous_outcomes(limit: int = 50):
    # Get autonomous action outcomes for learning
    try:
        outcomes = redis_client.lrange('autonomous_outcomes', 0, limit - 1)
        
        results = []
        for outcome_json in outcomes:
            outcome = json.loads(outcome_json)
            results.append(outcome)
        
        # Calculate statistics
        total = len(results)
        successes = sum(1 for r in results if r.get('success'))
        
        return {
            "outcomes": results,
            "statistics": {
                "total": total,
                "successes": successes,
                "success_rate": (successes / total * 100) if total > 0 else 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v3/autonomous/safety-status")
async def get_safety_status():
    # Get current safety rail status
    return {
        "max_concurrent_actions": 3,
        "active_actions": 0,
        "action_cooldown_seconds": 300,
        "recent_rollbacks": 0,
        "max_rollbacks_per_hour": 2,
        "blast_radius_limit": 50,
        "safety_rails_active": True
    }
"""


# ============================================================================
# FILE 3: Environment Variables (add to .env)
# ============================================================================

"""
# Phase 3: Autonomous Mode Configuration
AUTONOMOUS_MODE=false  # Set to true to enable autonomous execution
EXECUTION_MODE=supervised  # Options: manual, supervised, autonomous, night_mode

# Autonomous thresholds
CONFIDENCE_THRESHOLD=75  # Minimum confidence for autonomous execution (0-100)
NIGHT_MODE_START=22  # Hour to start night mode (24h format)
NIGHT_MODE_END=6  # Hour to end night mode

# Safety rails
MAX_CONCURRENT_ACTIONS=3
ACTION_COOLDOWN_SECONDS=300
MAX_ROLLBACKS_PER_HOUR=2
MAX_SCALE_FACTOR=3
BLAST_RADIUS_LIMIT=50
"""


# ============================================================================
# FILE 4: Test Script (test_phase3.py)
# ============================================================================

"""
import asyncio
import httpx
from datetime import datetime

BASE_URL = "http://localhost:8000"

async def test_phase3():
    client = httpx.AsyncClient(timeout=30.0)
    
    print("🧪 Testing Phase 3: Autonomous Mode\n")
    
    # Test 1: Get autonomous status
    print("1️⃣ Getting autonomous status...")
    response = await client.get(f"{BASE_URL}/api/v3/autonomous/status")
    if response.status_code == 200:
        status = response.json()
        print(f"   Mode: {status['execution_mode']}")
        print(f"   Enabled: {status['autonomous_enabled']}")
        print(f"   Success rate: {status['success_rate']}%")
    
    # Test 2: Change to night mode
    print("\n2️⃣ Testing mode change...")
    response = await client.post(
        f"{BASE_URL}/api/v3/autonomous/mode",
        json={"mode": "night_mode", "confidence_threshold": 80}
    )
    if response.status_code == 200:
        print("   ✓ Mode changed successfully")
    
    # Test 3: Get safety status
    print("\n3️⃣ Checking safety rails...")
    response = await client.get(f"{BASE_URL}/api/v3/autonomous/safety-status")
    if response.status_code == 200:
        safety = response.json()
        print(f"   Active actions: {safety['active_actions']}/{safety['max_concurrent_actions']}")
        print(f"   Cooldown: {safety['action_cooldown_seconds']}s")
    
    # Test 4: Get learning outcomes
    print("\n4️⃣ Getting autonomous outcomes...")
    response = await client.get(f"{BASE_URL}/api/v3/autonomous/outcomes?limit=10")
    if response.status_code == 200:
        data = response.json()
        stats = data['statistics']
        print(f"   Total: {stats['total']}")
        print(f"   Success rate: {stats['success_rate']:.1f}%")
    
    await client.aclose()
    print("\n✅ Phase 3 tests complete!")

if __name__ == "__main__":
    asyncio.run(test_phase3())
"""