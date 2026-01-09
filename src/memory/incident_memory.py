"""
Incident Memory - Phase 2: Learning System
Learns from past incidents to improve future recommendations
"""

import json
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import statistics

class IncidentMemory:
    """
    Stores and learns from incident history to improve future responses
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
        
    def record_incident(
        self,
        incident_id: str,
        service: str,
        root_cause: Dict,
        anomalies: List[Dict],
        actions_taken: List[Dict],
        resolution_time_seconds: float,
        was_successful: bool
    ) -> Dict:
        """
        Record an incident with full context for learning
        """
        incident_record = {
            "id": incident_id,
            "service": service,
            "root_cause": root_cause,
            "anomalies": anomalies,
            "actions_taken": actions_taken,
            "resolution_time_seconds": resolution_time_seconds,
            "was_successful": was_successful,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "symptoms": self._extract_symptoms(anomalies),
            "deployed_recently": self._check_recent_deployment(service),
        }
        
        # Store incident
        self.redis.setex(
            f"incident_memory:{incident_id}",
            365 * 86400,  # Keep for 1 year
            json.dumps(incident_record)
        )
        
        # Add to service history
        self.redis.lpush(f"incident_history:{service}", incident_id)
        
        # Update pattern database
        self._update_pattern_database(incident_record)
        
        print(f"[MEMORY] Recorded incident {incident_id} for {service}")
        return incident_record
    
    def find_similar_incidents(
        self,
        anomalies: List[Dict],
        service: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        Find similar past incidents based on symptoms
        """
        current_symptoms = self._extract_symptoms(anomalies)
        
        # Get all incidents for this service
        incident_ids = self.redis.lrange(f"incident_history:{service}", 0, 99)
        
        similar_incidents = []
        
        for incident_id in incident_ids:
            incident_data = self.redis.get(f"incident_memory:{incident_id.decode('utf-8')}")
            if not incident_data:
                continue
            
            incident = json.loads(incident_data)
            
            # Calculate similarity score
            similarity = self._calculate_similarity(
                current_symptoms,
                incident['symptoms']
            )
            
            if similarity > 0.5:  # Threshold for "similar"
                incident['similarity_score'] = similarity
                similar_incidents.append(incident)
        
        # Sort by similarity and recency
        similar_incidents.sort(
            key=lambda x: (x['similarity_score'], x['recorded_at']),
            reverse=True
        )
        
        return similar_incidents[:limit]
    
    def get_recommended_actions(
        self,
        anomalies: List[Dict],
        service: str
    ) -> List[Dict]:
        """
        Get recommended actions based on past successful resolutions
        """
        similar_incidents = self.find_similar_incidents(anomalies, service)
        
        if not similar_incidents:
            return []
        
        # Aggregate successful actions
        action_scores = defaultdict(lambda: {"count": 0, "success_rate": 0, "avg_resolution_time": 0})
        
        for incident in similar_incidents:
            if not incident['was_successful']:
                continue
            
            for action in incident['actions_taken']:
                action_key = f"{action['action_type']}_{action.get('params', {})}"
                action_scores[action_key]["count"] += 1
                action_scores[action_key]["success_rate"] += 1
                action_scores[action_key]["avg_resolution_time"] += incident['resolution_time_seconds']
                action_scores[action_key]["example"] = action
        
        # Calculate averages and sort
        recommendations = []
        for action_key, stats in action_scores.items():
            if stats["count"] > 0:
                recommendations.append({
                    "action": stats["example"],
                    "success_count": stats["count"],
                    "success_rate": (stats["success_rate"] / stats["count"]) * 100,
                    "avg_resolution_time": stats["avg_resolution_time"] / stats["count"],
                    "confidence": min(stats["count"] * 10, 100)  # More occurrences = higher confidence
                })
        
        recommendations.sort(key=lambda x: (x['success_rate'], -x['avg_resolution_time']), reverse=True)
        
        return recommendations[:3]
    
    def get_service_insights(self, service: str) -> Dict:
        """
        Get insights about a service's incident patterns
        """
        incident_ids = self.redis.lrange(f"incident_history:{service}", 0, 99)
        
        if not incident_ids:
            return {"message": "No incident history for this service"}
        
        incidents = []
        for incident_id in incident_ids:
            incident_data = self.redis.get(f"incident_memory:{incident_id.decode('utf-8')}")
            if incident_data:
                incidents.append(json.loads(incident_data))
        
        # Calculate insights
        total_incidents = len(incidents)
        successful_resolutions = sum(1 for i in incidents if i['was_successful'])
        
        resolution_times = [i['resolution_time_seconds'] for i in incidents]
        avg_resolution_time = statistics.mean(resolution_times) if resolution_times else 0
        
        # Most common root causes
        root_causes = defaultdict(int)
        for incident in incidents:
            cause = incident['root_cause'].get('description', 'Unknown')
            root_causes[cause] += 1
        
        top_causes = sorted(root_causes.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Most effective actions
        action_effectiveness = defaultdict(lambda: {"count": 0, "success": 0})
        for incident in incidents:
            if incident['was_successful']:
                for action in incident['actions_taken']:
                    action_type = action['action_type']
                    action_effectiveness[action_type]["count"] += 1
                    action_effectiveness[action_type]["success"] += 1
        
        effective_actions = [
            {
                "action_type": action_type,
                "success_rate": (stats["success"] / stats["count"] * 100) if stats["count"] > 0 else 0,
                "usage_count": stats["count"]
            }
            for action_type, stats in action_effectiveness.items()
        ]
        effective_actions.sort(key=lambda x: x['success_rate'], reverse=True)
        
        # Recent incident trend
        recent_incidents = [i for i in incidents if self._is_recent(i['recorded_at'], days=7)]
        
        return {
            "service": service,
            "total_incidents": total_incidents,
            "success_rate": (successful_resolutions / total_incidents * 100) if total_incidents > 0 else 0,
            "avg_resolution_time_minutes": avg_resolution_time / 60,
            "recent_incidents_7_days": len(recent_incidents),
            "top_root_causes": [{"cause": cause, "count": count} for cause, count in top_causes],
            "most_effective_actions": effective_actions[:3],
            "last_incident": incidents[0]['recorded_at'] if incidents else None
        }
    
    def _extract_symptoms(self, anomalies: List[Dict]) -> Dict:
        """
        Extract key symptoms from anomalies for pattern matching
        """
        symptoms = {
            "metrics": set(),
            "severity_critical": 0,
            "severity_high": 0,
            "latency_spike": False,
            "error_rate_spike": False,
            "memory_issue": False,
            "cpu_issue": False
        }
        
        for anomaly in anomalies:
            metric = anomaly.get('metric_name', '')
            symptoms["metrics"].add(metric)
            
            severity = anomaly.get('severity', 'low')
            if severity == 'critical':
                symptoms["severity_critical"] += 1
            elif severity == 'high':
                symptoms["severity_high"] += 1
            
            # Detect specific patterns
            if 'latency' in metric.lower():
                symptoms["latency_spike"] = True
            if 'error' in metric.lower():
                symptoms["error_rate_spike"] = True
            if 'memory' in metric.lower():
                symptoms["memory_issue"] = True
            if 'cpu' in metric.lower():
                symptoms["cpu_issue"] = True
        
        symptoms["metrics"] = list(symptoms["metrics"])
        return symptoms
    
    def _calculate_similarity(self, symptoms1: Dict, symptoms2: Dict) -> float:
        """
        Calculate similarity score between two incident symptom profiles
        """
        score = 0.0
        total_weight = 0.0
        
        # Compare metrics (weight: 0.4)
        metrics1 = set(symptoms1.get("metrics", []))
        metrics2 = set(symptoms2.get("metrics", []))
        if metrics1 and metrics2:
            overlap = len(metrics1 & metrics2)
            total = len(metrics1 | metrics2)
            score += (overlap / total) * 0.4
        total_weight += 0.4
        
        # Compare severity (weight: 0.3)
        severity_diff = abs(
            symptoms1.get("severity_critical", 0) - symptoms2.get("severity_critical", 0)
        ) + abs(
            symptoms1.get("severity_high", 0) - symptoms2.get("severity_high", 0)
        )
        severity_score = max(0, 1 - (severity_diff / 10))
        score += severity_score * 0.3
        total_weight += 0.3
        
        # Compare specific patterns (weight: 0.3)
        pattern_matches = 0
        pattern_checks = 0
        for key in ['latency_spike', 'error_rate_spike', 'memory_issue', 'cpu_issue']:
            if symptoms1.get(key) == symptoms2.get(key):
                pattern_matches += 1
            pattern_checks += 1
        
        if pattern_checks > 0:
            score += (pattern_matches / pattern_checks) * 0.3
        total_weight += 0.3
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def _check_recent_deployment(self, service: str) -> bool:
        """Check if there was a recent deployment"""
        try:
            recent_time = datetime.now(timezone.utc).timestamp() - (30 * 60)  # 30 minutes
            deployments = self.redis.zrangebyscore(
                f"deployments:{service}",
                recent_time,
                '+inf'
            )
            return len(deployments) > 0
        except Exception:
            return False
    
    def _is_recent(self, timestamp: str, days: int = 7) -> bool:
        """Check if timestamp is within last N days"""
        incident_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return incident_time.replace(tzinfo=None) > cutoff.replace(tzinfo=None)
    
    def _update_pattern_database(self, incident: Dict):
        """
        Update pattern database for ML/analytics
        """
        pattern_key = f"pattern:{incident['service']}"
        
        # Create pattern signature
        pattern = {
            "symptoms": json.dumps(incident['symptoms'], sort_keys=True),
            "root_cause": incident['root_cause']['description'],
            "actions": [a['action_type'] for a in incident['actions_taken']],
            "success": incident['was_successful'],
            "timestamp": incident['recorded_at']
        }
        
        # Store in pattern database
        self.redis.lpush(pattern_key, json.dumps(pattern))
        self.redis.ltrim(pattern_key, 0, 999)  # Keep last 1000 patterns
    
    def get_learning_stats(self) -> Dict:
        """
        Get overall learning statistics
        """
        # Count total incidents across all services
        all_services = set()
        for key in self.redis.scan_iter("incident_history:*"):
            service = key.decode('utf-8').split(':')[1]
            all_services.add(service)
        
        total_incidents = 0
        total_actions = 0
        
        for service in all_services:
            incident_ids = self.redis.lrange(f"incident_history:{service}", 0, -1)
            total_incidents += len(incident_ids)
            
            # Count actions
            for incident_id in incident_ids:
                incident_data = self.redis.get(f"incident_memory:{incident_id.decode('utf-8')}")
                if incident_data:
                    incident = json.loads(incident_data)
                    total_actions += len(incident.get('actions_taken', []))
        
        return {
            "total_incidents_learned": total_incidents,
            "total_actions_recorded": total_actions,
            "services_monitored": len(all_services),
            "learning_enabled": True,
            "pattern_database_size": total_incidents
        }