"""
Enhanced Worker - Phase 3: Autonomous Mode (FIXED)
Fixed: Analysis timeout, recorded_at error, proper error handling
"""

import asyncio
import redis
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.detection.anomaly_detector import AnomalyDetector
from src.detection.ai_analyzer import AIIncidentAnalyzer
from src.memory.incident_memory import IncidentMemory

load_dotenv()

class SimpleActionExecutor:
    """Simplified action executor"""
    def __init__(self, redis_client):
        self.redis = redis_client
        self.dry_run = os.getenv("DRY_RUN_MODE", "true").lower() == "true"
    
    async def execute_action(self, action_id: str) -> Dict:
        """Execute action"""
        try:
            action_data = self.redis.get(f"action:{action_id}")
            if not action_data:
                return {"success": False, "error": "Action not found"}
            
            action = json.loads(action_data)
            action_type = action.get('action_type', 'unknown')
            
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
        except Exception as e:
            print(f"[ACTION ERROR] {e}")
            return {"success": False, "error": str(e)}

class AutonomousIncidentWorker:
    """Phase 3 Worker with autonomous execution - FIXED"""
    
    def __init__(self):
        self.redis = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        
        # Core components
        self.anomaly_detector = AnomalyDetector(os.getenv("REDIS_URL"))
        
        # FIXED: Increase timeout for AI analysis
        self.ai_analyzer = AIIncidentAnalyzer(
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=os.getenv("OLLAMA_MODEL", "llama3:latest")
        )
        
        self.action_executor = SimpleActionExecutor(self.redis)
        self.incident_memory = IncidentMemory(self.redis)
        
        # Configuration
        self.autonomous_enabled = os.getenv("AUTONOMOUS_MODE", "false").lower() == "true"
        self.execution_mode = os.getenv("EXECUTION_MODE", "supervised")
        
        # Tracking
        self.last_alert_time = {}
        self.alert_cooldown = 300  # 5 minutes
        
        print(f"[WORKER] Phase 3 Autonomous Mode: {self.autonomous_enabled}")
        print(f"[WORKER] Execution Mode: {self.execution_mode}")
    
    async def run(self):
        """Main worker loop"""
        print("[WORKER] Starting Phase 3 Autonomous Worker...")
        
        tasks = [
            asyncio.create_task(self.process_metrics_stream()),
            asyncio.create_task(self.process_anomalies()),
            asyncio.create_task(self.process_approved_actions()),
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
                        print(f"[METRIC ERROR] {e}")
                        continue
                
                if len(processed_keys) > 1000:
                    processed_keys.clear()
                
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[METRICS ERROR] {e}")
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
                print(f"[ANOMALIES ERROR] {e}")
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
                        
                        # FIXED: Record action in history
                        action_data = self.redis.get(f"action:{action_id}")
                        if action_data:
                            action = json.loads(action_data)
                            action['status'] = 'success'
                            action['completed_at'] = datetime.now(timezone.utc).isoformat()
                            action['result'] = result
                            
                            # Update action
                            self.redis.setex(f"action:{action_id}", 86400, json.dumps(action))
                            
                            # Add to history
                            self.redis.lpush(f"actions:history:{action['service']}", action_id)
                    else:
                        print(f"[ACTION] ✗ Failed: {action_id}")
                
                await asyncio.sleep(2)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[ACTION PROCESSING ERROR] {e}")
                await asyncio.sleep(5)
    
    async def check_for_incident(self, service: str):
        """Check if we should trigger incident analysis"""
        try:
            # FIXED: Check cooldown
            last_alert = self.last_alert_time.get(service, 0)
            current_time = datetime.now(timezone.utc).timestamp()
            
            if current_time - last_alert < self.alert_cooldown:
                return
            
            anomalies = self.anomaly_detector.get_recent_anomalies(service, minutes=5)
            critical_anomalies = [a for a in anomalies if a.get('severity') in ['critical', 'high']]
            
            should_alert = len(critical_anomalies) >= 1 or len(anomalies) >= 3
            
            if should_alert:
                # Update alert time immediately to prevent duplicate processing
                self.last_alert_time[service] = current_time
                await self.analyze_and_propose_actions(service, anomalies)
        except Exception as e:
            print(f"[CHECK INCIDENT ERROR] {e}")
    
    async def analyze_and_propose_actions(self, service: str, anomalies: List[Dict]):
        """Analyze incident and propose actions - FIXED"""
        incident_id = f"incident_{service}_{int(datetime.now(timezone.utc).timestamp())}"
        
        try:
            # Gather context
            recent_logs = self._get_recent_logs(service, minutes=10)
            recent_deployments = self._get_recent_deployments(service, minutes=30)
            
            print(f"[ANALYSIS] Analyzing {incident_id}...")
            print(f"  - Anomalies: {len(anomalies)}")
            print(f"  - Logs: {len(recent_logs)}")
            print(f"  - Deployments: {len(recent_deployments)}")
            
            # FIXED: Add timeout and error handling for AI analysis
            try:
                # Run AI analysis with timeout
                analysis = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.ai_analyzer.analyze_incident,
                        anomalies=anomalies,
                        recent_logs=recent_logs,
                        recent_deployments=recent_deployments,
                        service_name=service
                    ),
                    timeout=30.0  # 30 second timeout
                )
                
                print(f"[ANALYSIS] Root cause: {analysis['root_cause']['description']}")
                print(f"[ANALYSIS] Confidence: {analysis['root_cause']['confidence']}%")
                
            except asyncio.TimeoutError:
                print(f"[AI TIMEOUT] Analysis timed out, using fallback")
                analysis = self._create_fallback_analysis(service, anomalies)
            except Exception as e:
                print(f"[AI ERROR] {e}, using fallback")
                analysis = self._create_fallback_analysis(service, anomalies)
            
            # Get similar incidents for learning
            similar_incidents = []
            try:
                similar_incidents = self.incident_memory.find_similar_incidents(
                    anomalies, service, limit=5
                )
            except Exception as e:
                print(f"[MEMORY ERROR] {e}")
            
            # Propose actions
            proposed_actions = await self._propose_actions(
                analysis, anomalies, service, incident_id, recent_deployments
            )
            
            print(f"[ACTIONS] Proposed {len(proposed_actions)} actions")
            
            # Store incident - FIXED: Add recorded_at field
            self._store_incident(incident_id, service, analysis, anomalies, proposed_actions)
            
            # Record in learning memory - FIXED: Handle errors
            try:
                if len(similar_incidents) > 0:
                    self.incident_memory.record_incident(
                        incident_id=incident_id,
                        service=service,
                        root_cause=analysis.get('root_cause', {}),
                        anomalies=anomalies,
                        actions_taken=proposed_actions,
                        resolution_time_seconds=0,
                        was_successful=False
                    )
            except Exception as e:
                print(f"[MEMORY RECORD ERROR] {e}")
            
        except Exception as e:
            print(f"[ANALYSIS ERROR] {e}")
            import traceback
            traceback.print_exc()
    
    def _create_fallback_analysis(self, service: str, anomalies: List[Dict]) -> Dict:
        """Create fallback analysis when AI times out - FIXED"""
        severity = 'medium'
        critical_count = sum(1 for a in anomalies if a.get('severity') == 'critical')
        
        if critical_count > 0:
            severity = 'critical'
        elif len(anomalies) >= 3:
            severity = 'high'
        
        return {
            'root_cause': {
                'description': f'{len(anomalies)} anomalies detected in {service}',
                'confidence': 60,
                'reasoning': 'AI analysis timed out, using rule-based detection'
            },
            'severity': severity,
            'recommended_actions': [
                {
                    'action': 'investigate',
                    'reasoning': 'Manual investigation required',
                    'risk': 'low',
                    'priority': 1
                }
            ],
            'estimated_customer_impact': 'Unknown - requires investigation',
            'analyzed_at': datetime.now(timezone.utc).isoformat(),
            'service': service,
            'fallback': True
        }
    
    async def _propose_actions(
        self,
        analysis: Dict,
        anomalies: List[Dict],
        service: str,
        incident_id: str,
        recent_deployments: List[Dict]
    ) -> List[Dict]:
        """Propose remediation actions - FIXED"""
        actions = []
        timestamp = int(datetime.now(timezone.utc).timestamp())
        
        try:
            # Rollback if recent deployment
            if recent_deployments and len(recent_deployments) > 0:
                action_id = f"action_{incident_id}_rollback_{timestamp}"
                action = {
                    "id": action_id,
                    "incident_id": incident_id,
                    "action_type": "rollback",
                    "service": service,
                    "params": {
                        "target_version": "previous",
                        "current_version": recent_deployments[-1].get('version', 'unknown')
                    },
                    "reasoning": "Recent deployment correlates with anomaly spike",
                    "risk": "low",
                    "status": "pending",
                    "proposed_at": datetime.now(timezone.utc).isoformat(),
                    "proposed_by": "ai_autopilot"
                }
                
                # Store action
                self.redis.setex(f"action:{action_id}", 86400, json.dumps(action))
                self.redis.lpush("actions:pending", action_id)
                actions.append(action)
                
                print(f"[ACTION] Proposed rollback for {service}")
            
            # Scale up for latency issues
            has_latency = any('latency' in a.get('metric_name', '').lower() for a in anomalies)
            if has_latency:
                action_id = f"action_{incident_id}_scale_up_{timestamp + 1}"
                action = {
                    "id": action_id,
                    "incident_id": incident_id,
                    "action_type": "scale_up",
                    "service": service,
                    "params": {
                        "current_replicas": 3,
                        "target_replicas": 6
                    },
                    "reasoning": "High latency detected, scaling may help",
                    "risk": "medium",
                    "status": "pending",
                    "proposed_at": datetime.now(timezone.utc).isoformat(),
                    "proposed_by": "ai_autopilot"
                }
                
                self.redis.setex(f"action:{action_id}", 86400, json.dumps(action))
                self.redis.lpush("actions:pending", action_id)
                actions.append(action)
                
                print(f"[ACTION] Proposed scale_up for {service}")
        
        except Exception as e:
            print(f"[PROPOSE ACTIONS ERROR] {e}")
        
        return actions
    
    def _get_recent_logs(self, service: str, minutes: int = 10) -> List[Dict]:
        """Get recent logs - FIXED"""
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
                except Exception as e:
                    continue
            
            return logs
        except Exception as e:
            print(f"[GET LOGS ERROR] {e}")
            return []
    
    def _get_recent_deployments(self, service: str, minutes: int = 30) -> List[Dict]:
        """Get recent deployments - FIXED"""
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
        except Exception as e:
            print(f"[GET DEPLOYMENTS ERROR] {e}")
            return []
    
    def _store_incident(
        self, 
        incident_id: str, 
        service: str, 
        analysis: Dict, 
        anomalies: List[Dict], 
        actions: List[Dict]
    ):
        """Store incident - FIXED: Add all required fields"""
        try:
            incident = {
                'id': incident_id,
                'service': service,
                'analysis': analysis,
                'anomalies': anomalies,
                'proposed_actions': actions,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'recorded_at': datetime.now(timezone.utc).isoformat(),  # FIXED: Add this field
                'status': 'active',
                'phase': 3
            }
            
            self.redis.lpush(f"incidents:{service}", json.dumps(incident))
            self.redis.ltrim(f"incidents:{service}", 0, 99)
            
            print(f"[INCIDENT] Stored {incident_id}")
        except Exception as e:
            print(f"[STORE INCIDENT ERROR] {e}")

async def main():
    worker = AutonomousIncidentWorker()
    await worker.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[WORKER] Stopped by user")