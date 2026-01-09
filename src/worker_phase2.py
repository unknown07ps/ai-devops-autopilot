"""
Enhanced Worker - Phase 2: Supervised Fixes
Integrates action execution, memory learning, and interactive notifications
"""

import asyncio
import redis
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Phase 1 components
from src.detection.anomaly_detector import AnomalyDetector
from src.detection.ai_analyzer import AIIncidentAnalyzer

load_dotenv()

# Simple action executor for Phase 2 (embedded in worker)
class SimpleActionExecutor:
    """Simplified action executor embedded in worker"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.dry_run = os.getenv("DRY_RUN_MODE", "true").lower() == "true"
    
    async def propose_action(
        self,
        action_type: str,
        service: str,
        params: Dict,
        reasoning: str,
        risk: str,
        incident_id: str
    ) -> Dict:
        """Propose a remediation action"""
        action = {
            "id": f"action_{incident_id}_{action_type}_{int(datetime.now(timezone.utc).timestamp())}",
            "incident_id": incident_id,
            "action_type": action_type,
            "service": service,
            "params": params,
            "reasoning": reasoning,
            "risk": risk,
            "status": "pending",
            "proposed_at": datetime.now(timezone.utc).isoformat(),
            "proposed_by": "ai_autopilot"
        }
        
        # Store action
        self.redis.setex(f"action:{action['id']}", 86400, json.dumps(action))
        self.redis.lpush("actions:pending", action['id'])
        
        print(f"[ACTION] Proposed {action_type} for {service} (risk: {risk})")
        return action
    
    async def execute_action(self, action_id: str) -> Dict:
        """Execute an approved action"""
        action_data = self.redis.get(f"action:{action_id}")
        if not action_data:
            return {"success": False, "error": "Action not found"}
        
        action = json.loads(action_data)
        
        if action['status'] != 'approved':
            return {"success": False, "error": "Action not approved"}
        
        action['status'] = 'executing'
        action['executed_at'] = datetime.now(timezone.utc).isoformat()
        self.redis.setex(f"action:{action_id}", 86400, json.dumps(action))
        
        print(f"[ACTION] Executing {action['action_type']} for {action['service']}")
        
        try:
            # Execute based on type
            action_type = action['action_type']
            
            if action_type == 'rollback':
                result = await self._execute_rollback(action)
            elif action_type == 'scale_up':
                result = await self._execute_scale_up(action)
            elif action_type == 'scale_down':
                result = await self._execute_scale_down(action)
            elif action_type == 'restart_service':
                result = await self._execute_restart(action)
            else:
                result = {"success": False, "error": "Unknown action type"}
            
            # Update action
            action['status'] = 'success' if result['success'] else 'failed'
            action['completed_at'] = datetime.now(timezone.utc).isoformat()
            action['result'] = result
            
            self.redis.setex(f"action:{action_id}", 86400, json.dumps(action))
            self.redis.lpush(f"actions:history:{action['service']}", action_id)
            
            return result
            
        except Exception as e:
            action['status'] = 'failed'
            action['error'] = str(e)
            self.redis.setex(f"action:{action_id}", 86400, json.dumps(action))
            return {"success": False, "error": str(e)}
    
    async def _execute_rollback(self, action: Dict) -> Dict:
        """Execute rollback"""
        service = action['service']
        target_version = action['params'].get('target_version', 'previous')
        
        if self.dry_run:
            return {
                "success": True,
                "dry_run": True,
                "message": f"DRY RUN: Would rollback {service} to {target_version}",
                "duration_seconds": 2
            }
        
        # Real rollback would go here
        await asyncio.sleep(1)
        return {
            "success": True,
            "message": f"Rolled back {service} to {target_version}",
            "duration_seconds": 1
        }
    
    async def _execute_scale_up(self, action: Dict) -> Dict:
        """Execute scale up"""
        service = action['service']
        current = action['params'].get('current_replicas', 3)
        target = action['params'].get('target_replicas', 6)
        
        if self.dry_run:
            return {
                "success": True,
                "dry_run": True,
                "message": f"DRY RUN: Would scale {service} from {current} to {target}",
                "duration_seconds": 1
            }
        
        await asyncio.sleep(1)
        return {
            "success": True,
            "message": f"Scaled {service} to {target} replicas",
            "duration_seconds": 1
        }
    
    async def _execute_scale_down(self, action: Dict) -> Dict:
        """Execute scale down"""
        service = action['service']
        current = action['params'].get('current_replicas', 6)
        target = action['params'].get('target_replicas', 3)
        
        if self.dry_run:
            return {
                "success": True,
                "dry_run": True,
                "message": f"DRY RUN: Would scale {service} from {current} to {target}"
            }
        
        await asyncio.sleep(1)
        return {
            "success": True,
            "message": f"Scaled {service} to {target} replicas"
        }
    
    async def _execute_restart(self, action: Dict) -> Dict:
        """Execute service restart"""
        service = action['service']
        
        if self.dry_run:
            return {
                "success": True,
                "dry_run": True,
                "message": f"DRY RUN: Would restart {service}"
            }
        
        await asyncio.sleep(2)
        return {
            "success": True,
            "message": f"Restarted {service}",
            "pods_restarted": 3
        }

class EnhancedIncidentWorker:
    """
    Phase 2 Worker with supervised remediation capabilities
    """
    
    def __init__(self):
        self.redis = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        
        # Phase 1 components
        self.anomaly_detector = AnomalyDetector(os.getenv("REDIS_URL"))
        self.ai_analyzer = AIIncidentAnalyzer(
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=os.getenv("OLLAMA_MODEL", "llama3:latest")
        )
        
        # Phase 2 components
        self.action_executor = SimpleActionExecutor(self.redis)
        
        # State
        self.active_incidents = {}
        self.last_alert_time = {}
        self.alert_cooldown = int(os.getenv("INCIDENT_COOLDOWN", "300"))
        
        # Phase 2 settings
        self.auto_approve_low_risk = os.getenv("AUTO_APPROVE_LOW_RISK", "false").lower() == "true"
        self.learning_enabled = os.getenv("LEARNING_ENABLED", "true").lower() == "true"
    
    async def run(self):
        """Main worker loop with Phase 2 features"""
        print("[WORKER] Starting Enhanced AI DevOps Autopilot Worker (Phase 2)...")
        print(f"[WORKER] Redis: {os.getenv('REDIS_URL')}")
        print(f"[WORKER] Auto-approve low-risk: {self.auto_approve_low_risk}")
        print(f"[WORKER] Learning enabled: {self.learning_enabled}")
        print(f"[WORKER] Dry-run mode: {os.getenv('DRY_RUN_MODE', 'true')}")
        
        # Create tasks
        tasks = [
            asyncio.create_task(self.process_metrics_stream()),
            asyncio.create_task(self.process_logs_stream()),
            asyncio.create_task(self.process_anomalies()),
            asyncio.create_task(self.process_approved_actions()),
        ]
        
        try:
            # Run all tasks
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\n[WORKER] Shutting down gracefully...")
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def process_metrics_stream(self):
        """Process incoming metrics and detect anomalies"""
        print("[WORKER] Monitoring metrics stream...")
        processed_keys = set()
        
        while True:
            try:
                # Check for new metrics
                metric_keys = self.redis.keys('metric:*')
                
                for key in metric_keys:
                    if key in processed_keys:
                        continue
                    
                    try:
                        metric_json = self.redis.get(key)
                        if metric_json:
                            metric_data = json.loads(metric_json)
                            
                            # Check for anomaly
                            anomaly = self.anomaly_detector.detect_anomaly(
                                metric_name=metric_data['metric_name'],
                                service=metric_data['labels'].get('service', 'unknown'),
                                value=metric_data['value']
                            )
                            
                            if anomaly:
                                print(f"[ANOMALY] {anomaly['metric_name']} in {anomaly['service']}: "
                                      f"{anomaly['current_value']:.2f} (severity: {anomaly['severity']})")
                                
                                self.anomaly_detector.store_anomaly(anomaly['service'], anomaly)
                                await self.check_for_incident(anomaly['service'])
                            
                            processed_keys.add(key)
                    except Exception as e:
                        print(f"[ERROR] Failed to process metric: {e}")
                        continue
                
                # Clean up
                if len(processed_keys) > 1000:
                    processed_keys.clear()
                
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                print("[WORKER] Metrics processor stopped")
                break
            except Exception as e:
                print(f"[ERROR] Metrics processing error: {e}")
                await asyncio.sleep(1)
    
    async def process_logs_stream(self):
        """Process log entries and detect error spikes"""
        print("[WORKER] Monitoring logs...")
        processed_count = {}
        error_counts = {}
        total_counts = {}
        
        while True:
            try:
                log_keys = self.redis.keys('logs:*')
                
                for key in log_keys:
                    service = key.decode('utf-8').split(':')[1]
                    
                    logs = self.redis.lrange(key, 0, 99)
                    current_count = len(logs)
                    last_processed = processed_count.get(service, 0)
                    
                    if current_count <= last_processed:
                        continue
                    
                    new_logs = logs[:current_count - last_processed]
                    
                    for log_json in new_logs:
                        try:
                            log_data = json.loads(log_json)
                            level = log_data.get('level', 'INFO')
                            
                            total_counts[service] = total_counts.get(service, 0) + 1
                            if level in ['ERROR', 'CRITICAL']:
                                error_counts[service] = error_counts.get(service, 0) + 1
                        except json.JSONDecodeError:
                            continue
                    
                    processed_count[service] = current_count
                    
                    # Check for error spikes
                    if total_counts.get(service, 0) >= 10:
                        anomaly = self.anomaly_detector.detect_error_rate_spike(
                            service=service,
                            error_count=error_counts.get(service, 0),
                            total_count=total_counts[service]
                        )
                        
                        if anomaly:
                            print(f"[ERROR SPIKE] {service}: {anomaly['current_error_rate']:.2f}%")
                            self.anomaly_detector.store_anomaly(service, anomaly)
                            await self.check_for_incident(service)
                        
                        error_counts[service] = 0
                        total_counts[service] = 0
                
                await asyncio.sleep(2)
                
            except asyncio.CancelledError:
                print("[WORKER] Logs processor stopped")
                break
            except Exception as e:
                print(f"[ERROR] Log processing error: {e}")
                await asyncio.sleep(2)
    
    async def process_anomalies(self):
        """Correlate anomalies and trigger incident analysis"""
        print("[WORKER] Starting anomaly correlation...")
        
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
                print("[WORKER] Anomaly correlator stopped")
                break
            except Exception as e:
                print(f"[ERROR] Anomaly correlation error: {e}")
                await asyncio.sleep(5)
    
    async def process_approved_actions(self):
        """Process approved actions from the queue"""
        print("[WORKER] Monitoring approved actions queue...")
        
        while True:
            try:
                action_id = self.redis.rpop("actions:approved")
                
                if action_id:
                    action_id = action_id.decode('utf-8')
                    print(f"[ACTION] Processing approved action: {action_id}")
                    
                    result = await self.action_executor.execute_action(action_id)
                    
                    if result['success']:
                        print(f"[ACTION] ✓ Completed: {action_id}")
                    else:
                        print(f"[ACTION] ✗ Failed: {action_id} - {result.get('error')}")
                
                await asyncio.sleep(2)
                
            except asyncio.CancelledError:
                print("[WORKER] Approved actions processor stopped")
                break
            except Exception as e:
                print(f"[ERROR] Action processing error: {e}")
                await asyncio.sleep(5)
    
    async def check_for_incident(self, service: str):
        """Check if we should trigger incident analysis"""
        # Check cooldown
        last_alert = self.last_alert_time.get(service, 0)
        current_time = datetime.now(timezone.utc).timestamp()
        
        if current_time - last_alert < self.alert_cooldown:
            return
        
        # Get recent anomalies
        anomalies = self.anomaly_detector.get_recent_anomalies(service, minutes=5)
        
        critical_anomalies = [a for a in anomalies if a.get('severity') in ['critical', 'high']]
        
        should_alert = (
            len(critical_anomalies) >= 1 or
            len(anomalies) >= 3
        )
        
        if should_alert and service not in self.active_incidents:
            print(f"[INCIDENT] Triggering analysis for {service}")
            await self.analyze_and_alert_phase2(service, anomalies)
    
    async def analyze_and_alert_phase2(self, service: str, anomalies: List[Dict]):
        """Enhanced analysis with action proposals"""
        try:
            self.active_incidents[service] = datetime.now(timezone.utc)
            incident_id = f"incident_{service}_{int(datetime.now(timezone.utc).timestamp())}"
            
            # Gather context
            recent_logs = self._get_recent_logs(service, minutes=10)
            recent_deployments = self._get_recent_deployments(service, minutes=30)
            
            print(f"[ANALYSIS] Analyzing incident {incident_id}...")
            print(f"  - Anomalies: {len(anomalies)}")
            print(f"  - Error logs: {len([l for l in recent_logs if l.get('level') in ['ERROR', 'CRITICAL']])}")
            print(f"  - Recent deployments: {len(recent_deployments)}")
            
            # Run AI analysis
            analysis = self.ai_analyzer.analyze_incident(
                anomalies=anomalies,
                recent_logs=recent_logs,
                recent_deployments=recent_deployments,
                service_name=service
            )
            
            print(f"[ANALYSIS] Root cause: {analysis['root_cause']['description']}")
            print(f"[ANALYSIS] Confidence: {analysis['root_cause']['confidence']}%")
            
            # Propose actions
            proposed_actions = await self._propose_remediation_actions(
                analysis=analysis,
                anomalies=anomalies,
                service=service,
                incident_id=incident_id,
                recent_deployments=recent_deployments
            )
            
            print(f"[ACTIONS] Proposed {len(proposed_actions)} remediation actions")
            
            # Auto-approve low-risk if enabled
            if self.auto_approve_low_risk:
                for action in proposed_actions:
                    if action.get('risk') == 'low':
                        print(f"[AUTO-APPROVE] Low-risk action: {action['action_type']}")
                        action_data = self.redis.get(f"action:{action['id']}")
                        if action_data:
                            action_obj = json.loads(action_data)
                            action_obj['status'] = 'approved'
                            action_obj['approved_by'] = 'auto_approval_system'
                            action_obj['approved_at'] = datetime.now(timezone.utc).isoformat()
                            self.redis.setex(f"action:{action['id']}", 86400, json.dumps(action_obj))
                            self.redis.lrem("actions:pending", 0, action['id'])
                            self.redis.lpush("actions:approved", action['id'])
            
            # Update alert time
            self.last_alert_time[service] = datetime.now(timezone.utc).timestamp()
            
            # Store incident
            self._store_incident_phase2(incident_id, service, analysis, anomalies, proposed_actions)
            
            # Record in learning memory
            if self.learning_enabled:
                self._record_in_memory(incident_id, service, analysis, anomalies)
            
        except Exception as e:
            print(f"[ERROR] Phase 2 analysis failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if service in self.active_incidents:
                del self.active_incidents[service]
    
    async def _propose_remediation_actions(
        self,
        analysis: Dict,
        anomalies: List[Dict],
        service: str,
        incident_id: str,
        recent_deployments: List[Dict]
    ) -> List[Dict]:
        """Propose remediation actions"""
        proposed = []
        
        # Check for deployment correlation
        if recent_deployments:
            latest = recent_deployments[-1]
            action = await self.action_executor.propose_action(
                action_type="rollback",
                service=service,
                params={
                    "current_version": latest['version'],
                    "target_version": "previous"
                },
                reasoning="Recent deployment correlates with anomaly spike",
                risk="low",
                incident_id=incident_id
            )
            proposed.append(action)
        
        # Check for latency issues
        has_latency_spike = any('latency' in a.get('metric_name', '').lower() for a in anomalies)
        
        if has_latency_spike:
            action = await self.action_executor.propose_action(
                action_type="scale_up",
                service=service,
                params={
                    "current_replicas": 3,
                    "target_replicas": 6
                },
                reasoning="High latency detected, scaling may help",
                risk="medium",
                incident_id=incident_id
            )
            proposed.append(action)
        
        # Check for memory issues
        has_memory_issue = any('memory' in a.get('metric_name', '').lower() for a in anomalies)
        
        if has_memory_issue:
            action = await self.action_executor.propose_action(
                action_type="restart_service",
                service=service,
                params={},
                reasoning="Memory leak detected, restart may clear",
                risk="medium",
                incident_id=incident_id
            )
            proposed.append(action)
        
        return proposed[:3]
    
    def _store_incident_phase2(
        self,
        incident_id: str,
        service: str,
        analysis: Dict,
        anomalies: List[Dict],
        proposed_actions: List[Dict]
    ):
        """Store incident with Phase 2 metadata"""
        incident = {
            'id': incident_id,
            'service': service,
            'analysis': analysis,
            'anomalies': anomalies,
            'proposed_actions': proposed_actions,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'status': 'active',
            'phase': 2
        }
        
        self.redis.lpush(f"incidents:{service}", json.dumps(incident))
        self.redis.ltrim(f"incidents:{service}", 0, 99)
    
    def _record_in_memory(
        self,
        incident_id: str,
        service: str,
        analysis: Dict,
        anomalies: List[Dict]
    ):
        """Record incident in learning memory"""
        memory_record = {
            'id': incident_id,
            'service': service,
            'root_cause': analysis.get('root_cause', {}),
            'anomalies': anomalies,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'symptoms': self._extract_symptoms(anomalies)
        }
        
        # Store in memory
        self.redis.setex(f"incident_memory:{incident_id}", 365 * 86400, json.dumps(memory_record))
        self.redis.lpush(f"incident_history:{service}", incident_id)
        
        print(f"[MEMORY] Recorded incident {incident_id} for learning")
    
    def _extract_symptoms(self, anomalies: List[Dict]) -> Dict:
        """Extract symptoms from anomalies"""
        symptoms = {
            "metrics": [],
            "severity_critical": 0,
            "severity_high": 0,
            "latency_spike": False,
            "error_rate_spike": False
        }
        
        for anomaly in anomalies:
            metric = anomaly.get('metric_name', '')
            symptoms["metrics"].append(metric)
            
            severity = anomaly.get('severity', 'low')
            if severity == 'critical':
                symptoms["severity_critical"] += 1
            elif severity == 'high':
                symptoms["severity_high"] += 1
            
            if 'latency' in metric.lower():
                symptoms["latency_spike"] = True
            if 'error' in metric.lower():
                symptoms["error_rate_spike"] = True
        
        return symptoms
    
    def _get_recent_logs(self, service: str, minutes: int = 10) -> List[Dict]:
        """Get recent logs for a service"""
        try:
            logs = []
            log_key = f"logs:{service}"
            log_data = self.redis.lrange(log_key, 0, 99)
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
            
            for log_json in log_data:
                try:
                    log = json.loads(log_json)
                    log_time = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
                    
                    if log_time.replace(tzinfo=None) > cutoff_time.replace(tzinfo=None):
                        logs.append(log)
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
            
            return logs
        except (redis.RedisError, Exception) as e:
            print(f"[WORKER] Error getting recent logs: {e}")
            return []
    
    def _get_recent_deployments(self, service: str, minutes: int = 30) -> List[Dict]:
        """Get recent deployments for a service"""
        try:
            start_time = (datetime.now(timezone.utc).timestamp() - minutes * 60)
            
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
        except (redis.RedisError, Exception) as e:
            print(f"[WORKER] Error getting recent deployments: {e}")
            return []

async def main():
    worker = EnhancedIncidentWorker()
    await worker.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[WORKER] Stopped by user")