import asyncio
import redis
import json
import os
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv

# Import our modules
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from detection.anomaly_detector import AnomalyDetector
from detection.ai_analyzer import AIIncidentAnalyzer
from api.slack_notifier import SlackNotifier

load_dotenv()

class IncidentWorker:
    """
    Background worker that processes events and detects incidents
    """
    
    def __init__(self):
        self.redis = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        self.anomaly_detector = AnomalyDetector(os.getenv("REDIS_URL"))
        # Use Ollama instead of Anthropic
        self.ai_analyzer = AIIncidentAnalyzer(
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=os.getenv("OLLAMA_MODEL", "llama3:latest")
        )
        self.slack = SlackNotifier(os.getenv("SLACK_WEBHOOK_URL"))
        
        # Processing state
        self.active_incidents = {}
        self.last_alert_time = {}
        self.alert_cooldown = 300  # 5 minutes between alerts for same service
    
    async def run(self):
        """
        Main worker loop
        """
        print("[WORKER] Starting AI DevOps Autopilot Worker...")
        print(f"[WORKER] Redis: {os.getenv('REDIS_URL')}")
        print(f"[WORKER] Slack configured: {bool(os.getenv('SLACK_WEBHOOK_URL'))}")
        
        # Test Slack connection
        if os.getenv('SLACK_WEBHOOK_URL'):
            success = await self.slack.send_test_alert()
            if success:
                print("[WORKER] ✓ Slack connection verified")
            else:
                print("[WORKER] ✗ Slack connection failed")
        
        # Start processing streams
        await asyncio.gather(
            self.process_metrics_stream(),
            self.process_logs_stream(),
            self.process_anomalies(),
        )
    
    async def process_metrics_stream(self):
        """
        Process incoming metrics and detect anomalies
        """
        print("[WORKER] Monitoring metrics stream...")
        last_id = b'0'
        
        while True:
            try:
                # Use blocking read with timeout
                streams = self.redis.xread(
                    {'events:metrics': last_id},
                    count=10,
                    block=1000  # 1 second timeout
                )
                
                if not streams:
                    await asyncio.sleep(0.1)
                    continue
                
                for stream_name, messages in streams:
                    for message_id, data in messages:
                        last_id = message_id
                        
                        # Parse metric
                        metric_data = json.loads(data[b'data'])
                        
                        # Check for anomaly
                        anomaly = self.anomaly_detector.detect_anomaly(
                            metric_name=metric_data['metric_name'],
                            service=metric_data['labels'].get('service', 'unknown'),
                            value=metric_data['value']
                        )
                        
                        if anomaly:
                            print(f"[ANOMALY] {anomaly['metric_name']} in {anomaly['service']}: "
                                  f"{anomaly['current_value']:.2f} (severity: {anomaly['severity']})")
                            
                            # Store anomaly for correlation
                            self.anomaly_detector.store_anomaly(anomaly['service'], anomaly)
                            
                            # Check if we should trigger incident analysis
                            await self.check_for_incident(anomaly['service'])
                
            except redis.exceptions.ResponseError as e:
                if 'unknown command' in str(e).lower():
                    print(f"[ERROR] Redis command not supported. Using fallback polling method...")
                    # Fall back to simple list-based approach
                    await self.process_metrics_fallback()
                    return
                else:
                    print(f"[ERROR] Metrics processing error: {e}")
                    await asyncio.sleep(1)
            except Exception as e:
                print(f"[ERROR] Metrics processing error: {e}")
                await asyncio.sleep(1)
    
    async def process_metrics_fallback(self):
        """
        Fallback method using simple lists instead of streams
        """
        print("[WORKER] Using fallback polling for metrics...")
        processed_count = 0
        
        while True:
            try:
                # Check for new metrics in a simple list
                metric_keys = self.redis.keys('metric:*')
                
                for key in metric_keys[processed_count:]:
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
                
                processed_count = len(metric_keys)
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"[ERROR] Fallback metrics processing: {e}")
                await asyncio.sleep(1)
    
    async def process_logs_stream(self):
        """
        Process log entries and detect error spikes
        """
        print("[WORKER] Monitoring logs stream...")
        last_id = b'0'
        error_counts = {}
        total_counts = {}
        
        while True:
            try:
                streams = self.redis.xread(
                    {'events:logs': last_id},
                    count=50,
                    block=1000
                )
                
                if not streams:
                    await asyncio.sleep(0.1)
                    continue
                
                for stream_name, messages in streams:
                    for message_id, data in messages:
                        last_id = message_id
                        
                        log_data = json.loads(data[b'data'])
                        service = log_data.get('service', 'unknown')
                        level = log_data.get('level', 'INFO')
                        
                        # Track error rates
                        total_counts[service] = total_counts.get(service, 0) + 1
                        if level in ['ERROR', 'CRITICAL']:
                            error_counts[service] = error_counts.get(service, 0) + 1
                            print(f"[ERROR LOG] {service}: {log_data.get('message', '')[:80]}")
                        
                        # Check for error rate spikes every 10 logs
                        if total_counts[service] % 10 == 0 and total_counts[service] > 0:
                            anomaly = self.anomaly_detector.detect_error_rate_spike(
                                service=service,
                                error_count=error_counts.get(service, 0),
                                total_count=total_counts[service]
                            )
                            
                            if anomaly:
                                print(f"[ERROR SPIKE] {service}: "
                                      f"{anomaly['current_error_rate']:.2f}% error rate")
                                
                                self.anomaly_detector.store_anomaly(service, anomaly)
                                await self.check_for_incident(service)
                            
                            # Reset counters
                            error_counts[service] = 0
                            total_counts[service] = 0
                
            except redis.exceptions.ResponseError as e:
                if 'unknown command' in str(e).lower():
                    print(f"[WORKER] Streams not available, skipping log monitoring")
                    return
                else:
                    print(f"[ERROR] Log processing error: {e}")
                    await asyncio.sleep(1)
            except Exception as e:
                print(f"[ERROR] Log processing error: {e}")
                await asyncio.sleep(1)
    
    async def process_anomalies(self):
        """
        Correlate anomalies and trigger incident analysis
        """
        print("[WORKER] Starting anomaly correlation...")
        
        while True:
            try:
                # Check all services with recent anomalies
                services = set()
                
                # Scan for recent anomaly streams or keys
                for key in self.redis.scan_iter("recent_anomalies:*"):
                    service = key.decode('utf-8').split(':')[1]
                    services.add(service)
                
                # Check each service
                for service in services:
                    await self.check_for_incident(service)
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                print(f"[ERROR] Anomaly correlation error: {e}")
                await asyncio.sleep(5)
    
    async def check_for_incident(self, service: str):
        """
        Check if we should trigger incident analysis for a service
        """
        # Check cooldown
        last_alert = self.last_alert_time.get(service, 0)
        if datetime.utcnow().timestamp() - last_alert < self.alert_cooldown:
            return
        
        # Get recent anomalies
        anomalies = self.anomaly_detector.get_recent_anomalies(service, minutes=5)
        
        # Trigger on multiple anomalies or high severity
        critical_anomalies = [a for a in anomalies if a.get('severity') in ['critical', 'high']]
        
        should_alert = (
            len(critical_anomalies) >= 1 or
            len(anomalies) >= 3
        )
        
        if should_alert and service not in self.active_incidents:
            print(f"[INCIDENT] Triggering analysis for {service}")
            await self.analyze_and_alert(service, anomalies)
    
    async def analyze_and_alert(self, service: str, anomalies: List[Dict]):
        """
        Perform AI analysis and send alert
        """
        try:
            # Mark as active
            self.active_incidents[service] = datetime.utcnow()
            
            # Gather context
            recent_logs = self._get_recent_logs(service, minutes=10)
            recent_deployments = self._get_recent_deployments(service, minutes=30)
            
            print(f"[ANALYSIS] Analyzing incident in {service}...")
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
            
            # Send Slack alert
            success = await self.slack.send_incident_alert(
                analysis=analysis,
                anomalies=anomalies
            )
            
            if success:
                print(f"[SLACK] ✓ Alert sent for {service}")
            else:
                print(f"[SLACK] ✗ Failed to send alert for {service}")
            
            # Update alert time
            self.last_alert_time[service] = datetime.utcnow().timestamp()
            
            # Store incident
            self._store_incident(service, analysis, anomalies)
            
        except Exception as e:
            print(f"[ERROR] Incident analysis failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Remove from active
            if service in self.active_incidents:
                del self.active_incidents[service]
    
    def _get_recent_logs(self, service: str, minutes: int = 10) -> List[Dict]:
        """Get recent logs for a service"""
        try:
            # Try to get from stream first
            start_time = int((datetime.utcnow().timestamp() - minutes * 60) * 1000)
            logs = []
            
            try:
                stream_data = self.redis.xrange(
                    'events:logs',
                    min=start_time,
                    max='+'
                )
                
                for msg_id, data in stream_data:
                    log = json.loads(data[b'data'])
                    if log.get('service') == service:
                        logs.append(log)
            except:
                # Fallback to list if streams don't work
                pass
            
            return logs
        except:
            return []
    
    def _get_recent_deployments(self, service: str, minutes: int = 30) -> List[Dict]:
        """Get recent deployments for a service"""
        try:
            start_time = (datetime.utcnow().timestamp() - minutes * 60)
            
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
                    'timestamp': datetime.fromtimestamp(timestamp).isoformat(),
                    'service': service
                })
            
            return deployments
        except:
            return []
    
    def _store_incident(self, service: str, analysis: Dict, anomalies: List[Dict]):
        """Store incident for future learning"""
        incident = {
            'service': service,
            'analysis': analysis,
            'anomalies': anomalies,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Store in Redis
        self.redis.lpush(f"incidents:{service}", json.dumps(incident))
        self.redis.ltrim(f"incidents:{service}", 0, 99)  # Keep last 100

async def main():
    worker = IncidentWorker()
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())