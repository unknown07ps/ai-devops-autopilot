import redis
import json
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict
import os

class AnomalyDetector:
    """
    Simple but effective anomaly detection using statistical methods
    Will get smarter over time with ML, but this works Day 1
    """
    
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.lookback_window = timedelta(minutes=15)
        self.std_dev_threshold = 2.5  # Trigger on 2.5 standard deviations
        
    def get_baseline(self, metric_name: str, service: str) -> Optional[Dict]:
        """
        Get baseline statistics for a metric
        """
        key = f"baseline:{service}:{metric_name}"
        data = self.redis.get(key)
        if data:
            return json.loads(data)
        return None
    
    def update_baseline(self, metric_name: str, service: str, value: float):
        """
        Update rolling baseline statistics
        """
        key = f"baseline:{service}:{metric_name}"
        baseline = self.get_baseline(metric_name, service) or {
            "mean": value,
            "std_dev": 0,
            "count": 0,
            "values": []
        }
        
        # Keep last 1000 values for rolling stats
        values = baseline["values"][-999:] + [value]
        
        # Calculate new statistics
        mean = statistics.mean(values)
        std_dev = statistics.stdev(values) if len(values) > 1 else 0
        
        baseline.update({
            "mean": mean,
            "std_dev": std_dev,
            "count": len(values),
            "values": values,
            "last_updated": datetime.utcnow().isoformat()
        })
        
        # Store with 7 day expiry
        self.redis.setex(key, 7 * 24 * 60 * 60, json.dumps(baseline))
        
        return baseline
    
    def detect_anomaly(self, metric_name: str, service: str, value: float) -> Optional[Dict]:
        """
        Detect if current value is anomalous
        Returns anomaly details if detected, None otherwise
        """
        baseline = self.get_baseline(metric_name, service)
        
        # Not enough data yet
        if not baseline or baseline["count"] < 10:
            self.update_baseline(metric_name, service, value)
            return None
        
        mean = baseline["mean"]
        std_dev = baseline["std_dev"]
        
        # Calculate z-score
        if std_dev == 0:
            z_score = 0
        else:
            z_score = abs(value - mean) / std_dev
        
        # Update baseline with new value
        self.update_baseline(metric_name, service, value)
        
        # Check if anomalous
        if z_score > self.std_dev_threshold:
            deviation_pct = ((value - mean) / mean) * 100 if mean != 0 else 0
            
            return {
                "metric_name": metric_name,
                "service": service,
                "current_value": value,
                "baseline_mean": mean,
                "baseline_std_dev": std_dev,
                "z_score": z_score,
                "deviation_percent": deviation_pct,
                "severity": self._calculate_severity(z_score),
                "detected_at": datetime.utcnow().isoformat()
            }
        
        return None
    
    def _calculate_severity(self, z_score: float) -> str:
        """
        Map z-score to severity level
        """
        if z_score > 4:
            return "critical"
        elif z_score > 3:
            return "high"
        elif z_score > 2.5:
            return "medium"
        else:
            return "low"
    
    def detect_error_rate_spike(self, service: str, error_count: int, total_count: int) -> Optional[Dict]:
        """
        Detect spikes in error rates
        """
        if total_count == 0:
            return None
            
        current_error_rate = (error_count / total_count) * 100
        
        # Get historical error rate
        baseline = self.get_baseline("error_rate", service)
        
        if not baseline or baseline["count"] < 10:
            self.update_baseline("error_rate", service, current_error_rate)
            return None
        
        # Error rates should be low - trigger on smaller deviations
        if current_error_rate > baseline["mean"] * 3 and current_error_rate > 1.0:
            return {
                "metric_name": "error_rate",
                "service": service,
                "current_error_rate": current_error_rate,
                "baseline_error_rate": baseline["mean"],
                "error_count": error_count,
                "total_count": total_count,
                "severity": "high" if current_error_rate > 5 else "medium",
                "detected_at": datetime.utcnow().isoformat()
            }
        
        self.update_baseline("error_rate", service, current_error_rate)
        return None
    
    def correlate_with_deployment(self, service: str, anomaly_time: datetime) -> Optional[Dict]:
        """
        Check if anomaly correlates with a recent deployment
        """
        # Look for deployments in the last 30 minutes
        start_time = (anomaly_time - timedelta(minutes=30)).timestamp()
        
        # Get recent deployments from sorted set
        recent_deploys = self.redis.zrangebyscore(
            f"deployments:{service}",
            start_time,
            anomaly_time.timestamp()
        )
        
        if recent_deploys:
            # Get the most recent deployment
            latest_version = recent_deploys[-1].decode('utf-8')
            deploy_time = self.redis.zscore(f"deployments:{service}", latest_version)
            
            time_since_deploy = (anomaly_time.timestamp() - deploy_time) / 60  # minutes
            
            return {
                "correlated": True,
                "version": latest_version,
                "time_since_deploy_minutes": time_since_deploy,
                "confidence": "high" if time_since_deploy < 10 else "medium"
            }
        
        return None
    
    def get_recent_anomalies(self, service: str, minutes: int = 30) -> List[Dict]:
        """
        Get all anomalies detected in the last N minutes
        """
        # Retrieve from Redis stream
        start_time = int((datetime.utcnow() - timedelta(minutes=minutes)).timestamp() * 1000)
        
        anomalies = []
        stream_data = self.redis.xrange(
            f"anomalies:{service}",
            min=start_time,
            max="+"
        )
        
        for msg_id, data in stream_data:
            anomalies.append(json.loads(data[b'data']))
        
        return anomalies
    
    def store_anomaly(self, service: str, anomaly: Dict):
        """
        Store detected anomaly for correlation and analysis
        """
        try:
            event = {
                "type": "anomaly",
                "data": json.dumps(anomaly)
            }
            # Try streams first
            try:
                self.redis.xadd(f"anomalies:{service}", event)
            except redis.exceptions.ResponseError as e:
                if 'unknown command' in str(e).lower():
                    # Fallback to simple list
                    pass
                else:
                    raise
        except:
            pass
        
        # Also store in a list for quick access (with expiry)
        key = f"recent_anomalies:{service}"
        self.redis.lpush(key, json.dumps(anomaly))
        self.redis.ltrim(key, 0, 99)  # Keep last 100
        self.redis.expire(key, 24 * 60 * 60)  # 24 hour expiry