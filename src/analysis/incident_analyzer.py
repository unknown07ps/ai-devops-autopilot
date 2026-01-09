"""
Incident Analyzer - Deep incident analysis with fingerprinting
Correlates incidents with patterns and provides resolution insights
"""

import json
import hashlib
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field, asdict


@dataclass
class IncidentAnalysis:
    """Complete analysis of an incident"""
    incident_id: str
    fingerprint: str
    service: str
    category: str
    subcategory: str
    severity: str
    
    # Pattern matching
    matched_patterns: List[Dict] = field(default_factory=list)
    best_match_pattern: str = None
    pattern_confidence: float = 0.0
    
    # Symptoms extracted
    symptoms: List[str] = field(default_factory=list)
    signals: List[str] = field(default_factory=list)
    
    # Root cause analysis
    root_cause: str = None
    root_cause_confidence: float = 0.0
    contributing_factors: List[str] = field(default_factory=list)
    
    # Historical correlation
    similar_incident_count: int = 0
    similar_incidents: List[Dict] = field(default_factory=list)
    historical_success_rate: float = 0.0
    avg_resolution_time_seconds: float = 0.0
    
    # Recommended actions
    recommended_actions: List[Dict] = field(default_factory=list)
    autonomous_safe: bool = False
    autonomous_reason: str = ""
    
    # Blast radius
    blast_radius: str = "unknown"
    affected_services: List[str] = field(default_factory=list)
    
    # Prediction
    predicted_resolution_time: float = 0.0
    recurrence_probability: float = 0.0
    
    timestamp: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class IncidentAnalyzer:
    """
    Deep incident analysis with pattern matching and historical correlation
    
    Features:
    - Incident fingerprinting for pattern matching
    - Historical incident correlation
    - Root cause identification
    - Action recommendations with success rates
    - Blast radius estimation
    - Recurrence prediction
    """
    
    def __init__(self, redis_client, knowledge_base=None, learning_engine=None):
        self.redis = redis_client
        self.knowledge_base = knowledge_base
        self.learning_engine = learning_engine
    
    def analyze_incident(
        self,
        incident_id: str,
        service: str,
        anomalies: List[Dict],
        logs: List[Dict] = None,
        deployments: List[Dict] = None,
        metrics: Dict = None
    ) -> IncidentAnalysis:
        """
        Perform comprehensive incident analysis
        
        Args:
            incident_id: Unique identifier for the incident
            service: Affected service name
            anomalies: Detected anomalies
            logs: Recent error logs
            deployments: Recent deployments
            metrics: Current metrics snapshot
            
        Returns:
            Complete IncidentAnalysis
        """
        
        # Create fingerprint
        fingerprint = self.create_fingerprint(anomalies, service)
        
        # Extract symptoms and signals
        symptoms = self._extract_symptoms(anomalies, logs)
        signals = self._extract_signals(logs)
        
        # Determine severity and category
        severity = self._determine_severity(anomalies)
        category, subcategory = self._categorize_incident(anomalies, logs)
        
        # Match against knowledge base patterns
        matched_patterns = []
        best_match_pattern = None
        pattern_confidence = 0.0
        
        if self.knowledge_base:
            matches = self.knowledge_base.find_matching_patterns(anomalies, logs, min_confidence=30.0)
            for pattern, score in matches[:5]:
                matched_patterns.append({
                    "pattern_id": pattern.pattern_id,
                    "name": pattern.name,
                    "confidence": score,
                    "autonomous_safe": pattern.autonomous_safe
                })
            
            if matches:
                best_pattern, pattern_confidence = matches[0]
                best_match_pattern = best_pattern.pattern_id
        
        # Find similar historical incidents
        similar_incidents = self._find_similar_incidents(fingerprint, service, symptoms)
        historical_stats = self._calculate_historical_stats(similar_incidents)
        
        # Determine root cause
        root_cause, root_cause_confidence = self._identify_root_cause(
            anomalies, logs, deployments, matched_patterns
        )
        
        # Get contributing factors
        contributing_factors = self._identify_contributing_factors(
            anomalies, logs, deployments, metrics
        )
        
        # Get recommended actions with historical success rates
        recommended_actions = self._get_recommended_actions(
            best_match_pattern,
            matched_patterns,
            similar_incidents
        )
        
        # Check if autonomous safe
        autonomous_safe, autonomous_reason = self._check_autonomous_safe(
            best_match_pattern,
            pattern_confidence,
            historical_stats
        )
        
        # Estimate blast radius
        blast_radius, affected_services = self._estimate_blast_radius(
            service, anomalies, metrics
        )
        
        # Predict resolution time and recurrence
        predicted_resolution = self._predict_resolution_time(
            best_match_pattern, historical_stats
        )
        recurrence_probability = self._predict_recurrence(
            fingerprint, similar_incidents
        )
        
        analysis = IncidentAnalysis(
            incident_id=incident_id,
            fingerprint=fingerprint,
            service=service,
            category=category,
            subcategory=subcategory,
            severity=severity,
            matched_patterns=matched_patterns,
            best_match_pattern=best_match_pattern,
            pattern_confidence=pattern_confidence,
            symptoms=symptoms,
            signals=signals,
            root_cause=root_cause,
            root_cause_confidence=root_cause_confidence,
            contributing_factors=contributing_factors,
            similar_incident_count=len(similar_incidents),
            similar_incidents=similar_incidents[:3],
            historical_success_rate=historical_stats.get("success_rate", 0),
            avg_resolution_time_seconds=historical_stats.get("avg_resolution_time", 0),
            recommended_actions=recommended_actions,
            autonomous_safe=autonomous_safe,
            autonomous_reason=autonomous_reason,
            blast_radius=blast_radius,
            affected_services=affected_services,
            predicted_resolution_time=predicted_resolution,
            recurrence_probability=recurrence_probability
        )
        
        # Store analysis for future reference
        self._store_analysis(analysis)
        
        return analysis
    
    def create_fingerprint(self, anomalies: List[Dict], service: str) -> str:
        """
        Create a unique fingerprint for incident identification
        
        Fingerprint is based on:
        - Service name
        - Anomaly types and metrics
        - Severity levels
        - Error patterns
        """
        features = [f"service:{service}"]
        
        for anomaly in anomalies:
            # Metric-based features
            if "metric_name" in anomaly:
                features.append(f"metric:{anomaly['metric_name']}")
            
            # Type features
            if "type" in anomaly:
                features.append(f"type:{anomaly['type']}")
            
            # Severity features
            severity = anomaly.get("severity", "unknown")
            features.append(f"severity:{severity}")
            
            # Threshold direction
            if anomaly.get("value", 0) > anomaly.get("threshold", 0):
                features.append("direction:above")
            else:
                features.append("direction:below")
        
        # Sort and deduplicate
        features = sorted(set(features))
        
        # Create hash
        fingerprint = hashlib.sha256("|".join(features).encode()).hexdigest()[:24]
        return fingerprint
    
    def _extract_symptoms(self, anomalies: List[Dict], logs: List[Dict]) -> List[str]:
        """Extract human-readable symptoms from anomalies"""
        symptoms = []
        
        for anomaly in anomalies:
            metric = anomaly.get("metric_name", "unknown")
            value = anomaly.get("value", 0)
            threshold = anomaly.get("threshold", 0)
            severity = anomaly.get("severity", "unknown")
            
            if value > threshold:
                symptoms.append(f"High {metric}: {value:.1f} (threshold: {threshold})")
            else:
                symptoms.append(f"Low {metric}: {value:.1f} (threshold: {threshold})")
        
        # Extract from logs
        if logs:
            error_count = sum(1 for log in logs if "error" in str(log).lower())
            if error_count > 0:
                symptoms.append(f"Error logs detected: {error_count} errors")
        
        return symptoms
    
    def _extract_signals(self, logs: List[Dict]) -> List[str]:
        """Extract key signals/keywords from logs"""
        signals = []
        
        if not logs:
            return signals
        
        # Keywords to look for
        keywords = [
            "OOMKilled", "CrashLoopBackOff", "timeout", "connection refused",
            "out of memory", "disk full", "CPU throttling", "deadlock",
            "replication lag", "certificate expired", "authentication failed",
            "rate limit", "quota exceeded", "health check failed"
        ]
        
        log_text = " ".join(str(log) for log in logs)
        
        for keyword in keywords:
            if keyword.lower() in log_text.lower():
                signals.append(keyword)
        
        return signals
    
    def _determine_severity(self, anomalies: List[Dict]) -> str:
        """Determine overall incident severity"""
        severity_weights = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        max_severity = "low"
        max_weight = 0
        
        for anomaly in anomalies:
            sev = anomaly.get("severity", "low")
            weight = severity_weights.get(sev, 1)
            if weight > max_weight:
                max_weight = weight
                max_severity = sev
        
        return max_severity
    
    def _categorize_incident(self, anomalies: List[Dict], logs: List[Dict]) -> Tuple[str, str]:
        """Categorize incident based on symptoms"""
        
        # Check for specific patterns in anomalies and logs
        log_text = " ".join(str(log) for log in (logs or []))
        anomaly_metrics = [a.get("metric_name", "") for a in anomalies]
        
        # Kubernetes indicators
        k8s_signals = ["pod", "container", "kubernetes", "kubelet", "node"]
        if any(signal in log_text.lower() for signal in k8s_signals):
            if "OOMKilled" in log_text or "memory" in str(anomaly_metrics):
                return "kubernetes", "memory"
            if "CrashLoopBackOff" in log_text:
                return "kubernetes", "pod_crash"
            return "kubernetes", "general"
        
        # Database indicators
        db_signals = ["database", "mysql", "postgres", "mongodb", "redis", "connection pool"]
        if any(signal in log_text.lower() for signal in db_signals):
            if "connection" in log_text.lower():
                return "database", "connection"
            if "slow query" in log_text.lower() or "deadlock" in log_text.lower():
                return "database", "performance"
            return "database", "general"
        
        # Network indicators
        if any(m in str(anomaly_metrics) for m in ["latency", "packet_loss", "timeout"]):
            return "network", "connectivity"
        
        # Application indicators
        if any(m in str(anomaly_metrics) for m in ["error_rate", "5xx", "exception"]):
            return "application", "errors"
        
        if any(m in str(anomaly_metrics) for m in ["cpu", "memory"]):
            return "application", "resources"
        
        return "unknown", "unknown"
    
    def _find_similar_incidents(
        self, 
        fingerprint: str, 
        service: str,
        symptoms: List[str]
    ) -> List[Dict]:
        """Find similar historical incidents"""
        similar = []
        
        try:
            # Look by fingerprint first (exact match)
            exact_matches = self.redis.lrange(f"incidents:by_fingerprint:{fingerprint}", 0, 9)
            for inc_id in exact_matches:
                inc_data = self.redis.get(f"incident:{inc_id}")
                if inc_data:
                    similar.append({
                        **json.loads(inc_data),
                        "match_type": "exact"
                    })
            
            # Look by service if not enough matches
            if len(similar) < 5:
                service_incidents = self.redis.lrange(f"incidents:by_service:{service}", 0, 49)
                for inc_id in service_incidents:
                    if len(similar) >= 10:
                        break
                    inc_data = self.redis.get(f"incident:{inc_id}")
                    if inc_data:
                        inc = json.loads(inc_data)
                        # Calculate symptom overlap
                        inc_symptoms = set(inc.get("symptoms", []))
                        current_symptoms = set(symptoms)
                        overlap = len(inc_symptoms & current_symptoms)
                        if overlap > 0:
                            similar.append({
                                **inc,
                                "match_type": "symptom",
                                "symptom_overlap": overlap
                            })
            
        except Exception as e:
            print(f"Error finding similar incidents: {e}")
        
        return similar
    
    def _calculate_historical_stats(self, similar_incidents: List[Dict]) -> Dict:
        """Calculate statistics from similar incidents"""
        if not similar_incidents:
            return {"success_rate": 0, "avg_resolution_time": 0, "count": 0}
        
        resolved = [i for i in similar_incidents if i.get("resolved", False)]
        resolution_times = [
            i.get("resolution_time_seconds", 0) 
            for i in resolved 
            if i.get("resolution_time_seconds", 0) > 0
        ]
        
        return {
            "success_rate": len(resolved) / len(similar_incidents) if similar_incidents else 0,
            "avg_resolution_time": sum(resolution_times) / len(resolution_times) if resolution_times else 0,
            "count": len(similar_incidents)
        }
    
    def _identify_root_cause(
        self,
        anomalies: List[Dict],
        logs: List[Dict],
        deployments: List[Dict],
        matched_patterns: List[Dict]
    ) -> Tuple[str, float]:
        """Identify the most likely root cause"""
        
        # Check for deployment correlation first
        if deployments:
            recent_deploy = deployments[0] if deployments else None
            if recent_deploy:
                deploy_time = recent_deploy.get("timestamp", "")
                # If deployment was recent (within 1 hour), likely cause
                return "Recent deployment change", 85.0
        
        # Use matched pattern's root causes
        if matched_patterns:
            best_pattern = matched_patterns[0]
            return f"Pattern match: {best_pattern.get('name', 'Unknown')}", best_pattern.get("confidence", 50.0)
        
        # Fallback to heuristics
        log_text = " ".join(str(log) for log in (logs or []))
        
        if "OOMKilled" in log_text or "out of memory" in log_text.lower():
            return "Memory exhaustion - application exceeded memory limits", 90.0
        
        if "connection" in log_text.lower() and "timeout" in log_text.lower():
            return "Connection timeout - downstream service unreachable", 75.0
        
        return "Unknown - requires investigation", 30.0
    
    def _identify_contributing_factors(
        self,
        anomalies: List[Dict],
        logs: List[Dict],
        deployments: List[Dict],
        metrics: Dict
    ) -> List[str]:
        """Identify factors that may have contributed to the incident"""
        factors = []
        
        # Check for high resource usage
        if metrics:
            if metrics.get("cpu_usage", 0) > 80:
                factors.append("High CPU usage before incident")
            if metrics.get("memory_usage", 0) > 85:
                factors.append("High memory usage before incident")
            if metrics.get("request_rate", 0) > metrics.get("avg_request_rate", 0) * 1.5:
                factors.append("Traffic spike detected")
        
        # Check for recent deployments
        if deployments:
            factors.append("Recent deployment in timeline")
        
        # Check for cascading failures
        if len(anomalies) > 3:
            factors.append("Multiple anomalies suggest cascading failure")
        
        return factors
    
    def _get_recommended_actions(
        self,
        best_match_pattern: str,
        matched_patterns: List[Dict],
        similar_incidents: List[Dict]
    ) -> List[Dict]:
        """Get recommended actions with success rates"""
        actions = []
        
        # Get actions from matched pattern
        if best_match_pattern and self.knowledge_base:
            pattern = self.knowledge_base.get_pattern(best_match_pattern)
            if pattern:
                for rec_action in pattern.recommended_actions:
                    # Get historical success rate if learning engine available
                    success_rate = 0.5
                    if self.learning_engine:
                        success_rate = self.learning_engine.get_action_success_rate(
                            best_match_pattern,
                            rec_action.action_type,
                            rec_action.action_category
                        )
                    
                    actions.append({
                        "action_type": rec_action.action_type,
                        "action_category": rec_action.action_category,
                        "pattern_confidence": rec_action.confidence,
                        "historical_success_rate": success_rate,
                        "combined_score": (rec_action.confidence * 0.6 + success_rate * 100 * 0.4),
                        "params": rec_action.params,
                        "requires_approval": rec_action.requires_approval
                    })
        
        # Look at what worked for similar incidents
        for inc in similar_incidents[:3]:
            if inc.get("resolved", False):
                for action in inc.get("actions_taken", [])[:2]:
                    if action not in [a["action_type"] for a in actions]:
                        actions.append({
                            "action_type": action.get("type", "unknown"),
                            "action_category": action.get("category", "unknown"),
                            "pattern_confidence": 50.0,
                            "historical_success_rate": 1.0,  # Worked before
                            "combined_score": 70.0,
                            "source": "historical"
                        })
        
        # Sort by combined score
        actions.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
        
        return actions[:5]
    
    def _check_autonomous_safe(
        self,
        best_match_pattern: str,
        pattern_confidence: float,
        historical_stats: Dict
    ) -> Tuple[bool, str]:
        """Check if incident can be handled autonomously"""
        
        if not best_match_pattern:
            return False, "No matching pattern found"
        
        if pattern_confidence < 70:
            return False, f"Pattern confidence too low: {pattern_confidence:.1f}%"
        
        # Check learning engine if available
        if self.learning_engine:
            is_safe, reason = self.learning_engine.is_autonomous_safe(best_match_pattern)
            return is_safe, reason
        
        # Check pattern's autonomous_safe flag
        if self.knowledge_base:
            pattern = self.knowledge_base.get_pattern(best_match_pattern)
            if pattern:
                if pattern.autonomous_safe:
                    return True, "Pattern marked as autonomous-safe"
                else:
                    return False, "Pattern requires manual approval"
        
        return False, "Insufficient data for autonomous execution"
    
    def _estimate_blast_radius(
        self,
        service: str,
        anomalies: List[Dict],
        metrics: Dict
    ) -> Tuple[str, List[str]]:
        """Estimate blast radius of the incident"""
        
        affected_services = [service]
        
        # Check for cross-service impact in anomalies
        for anomaly in anomalies:
            affected = anomaly.get("affected_services", [])
            for svc in affected:
                if svc not in affected_services:
                    affected_services.append(svc)
        
        # Determine radius
        if len(affected_services) == 1:
            radius = "low"
        elif len(affected_services) <= 3:
            radius = "medium"
        else:
            radius = "high"
        
        # Critical services escalate radius
        critical_services = ["auth", "payment", "database", "gateway"]
        if any(svc in service.lower() for svc in critical_services):
            radius = "high" if radius != "high" else "critical"
        
        return radius, affected_services
    
    def _predict_resolution_time(
        self,
        best_match_pattern: str,
        historical_stats: Dict
    ) -> float:
        """Predict time to resolution"""
        
        # Use historical average if available
        if historical_stats.get("avg_resolution_time", 0) > 0:
            return historical_stats["avg_resolution_time"]
        
        # Use pattern's average if available
        if best_match_pattern and self.knowledge_base:
            pattern = self.knowledge_base.get_pattern(best_match_pattern)
            if pattern:
                return pattern.resolution_time_avg_seconds
        
        return 300.0  # Default 5 minutes
    
    def _predict_recurrence(
        self,
        fingerprint: str,
        similar_incidents: List[Dict]
    ) -> float:
        """Predict probability of recurrence"""
        
        if not similar_incidents:
            return 0.1  # Low baseline
        
        # Count how many times this exact fingerprint appeared
        exact_matches = sum(1 for i in similar_incidents if i.get("match_type") == "exact")
        
        if exact_matches >= 5:
            return 0.9  # High recurrence
        elif exact_matches >= 3:
            return 0.7
        elif exact_matches >= 1:
            return 0.5
        else:
            return 0.2
    
    def _store_analysis(self, analysis: IncidentAnalysis):
        """Store analysis for future reference"""
        try:
            self.redis.setex(
                f"incident_analysis:{analysis.incident_id}",
                86400 * 30,  # 30 days
                json.dumps(asdict(analysis))
            )
            
            # Index by fingerprint
            self.redis.lpush(
                f"incidents:by_fingerprint:{analysis.fingerprint}",
                analysis.incident_id
            )
            self.redis.ltrim(f"incidents:by_fingerprint:{analysis.fingerprint}", 0, 99)
            
            # Index by service
            self.redis.lpush(
                f"incidents:by_service:{analysis.service}",
                analysis.incident_id
            )
            self.redis.ltrim(f"incidents:by_service:{analysis.service}", 0, 99)
            
        except Exception as e:
            print(f"Error storing analysis: {e}")
    
    def get_analysis(self, incident_id: str) -> Optional[IncidentAnalysis]:
        """Retrieve a stored analysis"""
        try:
            data = self.redis.get(f"incident_analysis:{incident_id}")
            if data:
                return IncidentAnalysis(**json.loads(data))
        except (json.JSONDecodeError, Exception) as e:
            logger.debug(f"Error getting analysis: {e}")
        return None


# Convenience function
def get_incident_analyzer(redis_client, knowledge_base=None, learning_engine=None) -> IncidentAnalyzer:
    """Get incident analyzer instance"""
    return IncidentAnalyzer(redis_client, knowledge_base, learning_engine)
