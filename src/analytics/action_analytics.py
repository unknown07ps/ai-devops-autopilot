"""
Action Analytics - Enterprise DevOps Automation
Provides analytics and insights on action effectiveness
"""

import json
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import statistics


class ActionAnalytics:
    """
    Comprehensive analytics for DevOps actions
    Tracks success rates, resolution times, and recommendations accuracy
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def get_overview_stats(self, days: int = 30) -> Dict:
        """Get overview statistics for the last N days"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        all_actions = self._get_all_actions(cutoff)
        
        total = len(all_actions)
        successes = sum(1 for a in all_actions if a.get("result", {}).get("success"))
        
        return {
            "period_days": days,
            "total_actions": total,
            "successful_actions": successes,
            "failed_actions": total - successes,
            "success_rate": round((successes / total * 100) if total > 0 else 0, 1),
            "actions_per_day": round(total / days, 1) if days > 0 else 0,
            "by_category": self._get_stats_by_category(all_actions),
            "by_action_type": self._get_stats_by_action_type(all_actions),
            "top_services": self._get_top_services(all_actions),
            "trend": self._get_trend(all_actions, days)
        }
    
    def get_action_success_trends(self, days: int = 30) -> Dict:
        """Get success rate trends over time"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        all_actions = self._get_all_actions(cutoff)
        
        # Group by day
        daily_stats = defaultdict(lambda: {"total": 0, "success": 0})
        
        for action in all_actions:
            timestamp = action.get("timestamp", "")
            try:
                date = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime('%Y-%m-%d')
                daily_stats[date]["total"] += 1
                if action.get("result", {}).get("success"):
                    daily_stats[date]["success"] += 1
            except (ValueError, TypeError):
                continue
        
        trend_data = []
        for date in sorted(daily_stats.keys()):
            stats = daily_stats[date]
            trend_data.append({
                "date": date,
                "total": stats["total"],
                "success": stats["success"],
                "success_rate": round((stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0, 1)
            })
        
        return {
            "period_days": days,
            "trend": trend_data,
            "average_success_rate": round(
                statistics.mean([d["success_rate"] for d in trend_data]) if trend_data else 0, 1
            )
        }
    
    def get_resolution_time_analysis(self, days: int = 30) -> Dict:
        """Analyze resolution times for incidents"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get incidents with resolution data
        incident_keys = list(self.redis.scan_iter("incident_memory:*"))
        
        resolution_times = []
        by_severity = defaultdict(list)
        by_action_type = defaultdict(list)
        
        for key in incident_keys[:1000]:  # Limit to last 1000
            data = self.redis.get(key)
            if not data:
                continue
            
            incident = json.loads(data)
            recorded_at = incident.get("recorded_at", "")
            
            try:
                incident_time = datetime.fromisoformat(recorded_at.replace('Z', '+00:00'))
                if incident_time < cutoff:
                    continue
            except (ValueError, TypeError):
                continue
            
            resolution_time = incident.get("resolution_time_seconds", 0)
            if resolution_time > 0:
                resolution_times.append(resolution_time)
                
                severity = incident.get("root_cause", {}).get("severity", "unknown")
                by_severity[severity].append(resolution_time)
                
                for action in incident.get("actions_taken", []):
                    action_type = action.get("action_type", "unknown")
                    by_action_type[action_type].append(resolution_time)
        
        return {
            "period_days": days,
            "total_incidents_analyzed": len(resolution_times),
            "average_resolution_seconds": round(statistics.mean(resolution_times), 1) if resolution_times else 0,
            "median_resolution_seconds": round(statistics.median(resolution_times), 1) if resolution_times else 0,
            "min_resolution_seconds": min(resolution_times) if resolution_times else 0,
            "max_resolution_seconds": max(resolution_times) if resolution_times else 0,
            "by_severity": {
                sev: {
                    "count": len(times),
                    "average_seconds": round(statistics.mean(times), 1) if times else 0
                }
                for sev, times in by_severity.items()
            },
            "by_action_type": {
                action: {
                    "count": len(times),
                    "average_seconds": round(statistics.mean(times), 1) if times else 0
                }
                for action, times in list(by_action_type.items())[:10]
            }
        }
    
    def get_action_effectiveness(self, action_type: str = None) -> Dict:
        """Analyze effectiveness of specific action types"""
        all_actions = self._get_all_actions()
        
        effectiveness = defaultdict(lambda: {
            "total": 0,
            "success": 0,
            "durations": [],
            "services": defaultdict(int)
        })
        
        for action in all_actions:
            a_type = action.get("action_type", "unknown")
            if action_type and a_type != action_type:
                continue
            
            effectiveness[a_type]["total"] += 1
            
            result = action.get("result", {})
            if result.get("success"):
                effectiveness[a_type]["success"] += 1
            
            duration = result.get("duration_seconds", 0)
            if duration > 0:
                effectiveness[a_type]["durations"].append(duration)
            
            service = action.get("params", {}).get("service") or \
                      action.get("params", {}).get("deployment") or \
                      "unknown"
            effectiveness[a_type]["services"][service] += 1
        
        analysis = {}
        for a_type, stats in effectiveness.items():
            analysis[a_type] = {
                "total_executions": stats["total"],
                "successful_executions": stats["success"],
                "success_rate": round((stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0, 1),
                "average_duration_seconds": round(
                    statistics.mean(stats["durations"]) if stats["durations"] else 0, 2
                ),
                "top_services": dict(sorted(
                    stats["services"].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5])
            }
        
        return {
            "action_type": action_type or "all",
            "effectiveness": analysis
        }
    
    def get_recommendation_accuracy(self) -> Dict:
        """Analyze accuracy of AI recommendations"""
        outcomes_data = self.redis.lrange('autonomous_outcomes', 0, 999)
        
        total = 0
        ai_recommended = 0
        ai_successful = 0
        by_confidence = defaultdict(lambda: {"total": 0, "success": 0})
        
        for outcome_json in outcomes_data:
            try:
                outcome = json.loads(outcome_json)
                total += 1
                
                if outcome.get("was_ai_recommended"):
                    ai_recommended += 1
                    if outcome.get("success"):
                        ai_successful += 1
                
                confidence = outcome.get("confidence", 0)
                confidence_bucket = f"{(confidence // 10) * 10}-{(confidence // 10) * 10 + 9}"
                by_confidence[confidence_bucket]["total"] += 1
                if outcome.get("success"):
                    by_confidence[confidence_bucket]["success"] += 1
            except json.JSONDecodeError:
                continue
        
        return {
            "total_outcomes": total,
            "ai_recommended_actions": ai_recommended,
            "ai_successful_actions": ai_successful,
            "ai_accuracy_rate": round((ai_successful / ai_recommended * 100) if ai_recommended > 0 else 0, 1),
            "by_confidence_bucket": {
                bucket: {
                    "total": stats["total"],
                    "success": stats["success"],
                    "accuracy": round((stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0, 1)
                }
                for bucket, stats in sorted(by_confidence.items())
            }
        }
    
    def get_service_health_summary(self) -> Dict:
        """Get health summary for all monitored services"""
        services_data = self.redis.lrange('services', 0, -1)
        incident_counts = defaultdict(int)
        action_counts = defaultdict(int)
        
        # Count incidents per service
        for key in self.redis.scan_iter("incident_history:*"):
            service = key.decode().split(":")[1]
            count = self.redis.llen(key)
            incident_counts[service] = count
        
        # Count actions per service
        all_actions = self._get_all_actions()
        for action in all_actions:
            service = action.get("params", {}).get("service") or \
                      action.get("params", {}).get("deployment") or \
                      "unknown"
            action_counts[service] += 1
        
        # Build health data
        services = []
        for service in set(list(incident_counts.keys()) + list(action_counts.keys())):
            incidents = incident_counts.get(service, 0)
            actions = action_counts.get(service, 0)
            
            # Calculate health score (lower incidents = better health)
            health_score = max(0, 100 - (incidents * 5) - (actions * 2))
            
            services.append({
                "service": service,
                "incident_count": incidents,
                "action_count": actions,
                "health_score": health_score,
                "status": "healthy" if health_score >= 80 else "warning" if health_score >= 50 else "critical"
            })
        
        services.sort(key=lambda x: x["health_score"])
        
        return {
            "total_services": len(services),
            "healthy_services": sum(1 for s in services if s["status"] == "healthy"),
            "warning_services": sum(1 for s in services if s["status"] == "warning"),
            "critical_services": sum(1 for s in services if s["status"] == "critical"),
            "services": services
        }
    
    def get_cost_impact_analysis(self, days: int = 30) -> Dict:
        """Analyze cost impact of automated actions"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        all_actions = self._get_all_actions(cutoff)
        
        # Estimated cost savings per action type (in minutes of engineer time)
        cost_per_action = {
            "rollback": 30,
            "scale_up": 15,
            "scale_down": 10,
            "restart_service": 10,
            "pod_restart": 5,
            "deployment_scale": 10,
            "rollout_restart": 15,
            "connection_pool_reset": 20,
            "slow_query_kill": 25,
            "default": 10
        }
        
        total_time_saved = 0
        by_action = defaultdict(int)
        
        for action in all_actions:
            if action.get("result", {}).get("success"):
                action_type = action.get("action_type", "default")
                time_saved = cost_per_action.get(action_type, cost_per_action["default"])
                total_time_saved += time_saved
                by_action[action_type] += time_saved
        
        # Assume average DevOps engineer cost of $75/hour
        hourly_rate = 75
        total_hours_saved = total_time_saved / 60
        total_cost_saved = total_hours_saved * hourly_rate
        
        return {
            "period_days": days,
            "total_automated_actions": len([a for a in all_actions if a.get("result", {}).get("success")]),
            "estimated_time_saved_minutes": total_time_saved,
            "estimated_time_saved_hours": round(total_hours_saved, 1),
            "estimated_cost_saved_usd": round(total_cost_saved, 2),
            "monthly_projection_usd": round((total_cost_saved / days) * 30, 2) if days > 0 else 0,
            "by_action_type": {
                action: {"minutes_saved": minutes, "cost_saved_usd": round((minutes / 60) * hourly_rate, 2)}
                for action, minutes in sorted(by_action.items(), key=lambda x: x[1], reverse=True)[:10]
            }
        }
    
    # Helper methods
    def _get_all_actions(self, cutoff: datetime = None) -> List[Dict]:
        """Get all actions from history"""
        actions = []
        
        history_keys = [
            "k8s_action_history",
            "cloud_action_history",
            "database_action_history",
            "cicd_action_history",
            "action_history"
        ]
        
        for key in history_keys:
            data = self.redis.lrange(key, 0, 999)
            for item in data:
                try:
                    action = json.loads(item)
                    
                    if cutoff:
                        timestamp = action.get("timestamp", "")
                        try:
                            action_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            if action_time < cutoff:
                                continue
                        except (ValueError, TypeError):
                            pass
                    
                    actions.append(action)
                except json.JSONDecodeError:
                    continue
        
        return actions
    
    def _get_stats_by_category(self, actions: List[Dict]) -> Dict:
        """Get statistics grouped by category"""
        stats = defaultdict(lambda: {"total": 0, "success": 0})
        
        for action in actions:
            category = action.get("category", "base")
            stats[category]["total"] += 1
            if action.get("result", {}).get("success"):
                stats[category]["success"] += 1
        
        return {
            cat: {
                "total": s["total"],
                "success": s["success"],
                "success_rate": round((s["success"] / s["total"] * 100) if s["total"] > 0 else 0, 1)
            }
            for cat, s in stats.items()
        }
    
    def _get_stats_by_action_type(self, actions: List[Dict]) -> Dict:
        """Get statistics grouped by action type"""
        stats = defaultdict(lambda: {"total": 0, "success": 0})
        
        for action in actions:
            action_type = action.get("action_type", "unknown")
            stats[action_type]["total"] += 1
            if action.get("result", {}).get("success"):
                stats[action_type]["success"] += 1
        
        # Return top 10 action types
        sorted_stats = sorted(stats.items(), key=lambda x: x[1]["total"], reverse=True)[:10]
        
        return {
            action_type: {
                "total": s["total"],
                "success": s["success"],
                "success_rate": round((s["success"] / s["total"] * 100) if s["total"] > 0 else 0, 1)
            }
            for action_type, s in sorted_stats
        }
    
    def _get_top_services(self, actions: List[Dict]) -> List[Dict]:
        """Get top services by action count"""
        service_counts = defaultdict(int)
        
        for action in actions:
            service = action.get("params", {}).get("service") or \
                      action.get("params", {}).get("deployment") or \
                      action.get("params", {}).get("pod_name") or \
                      "unknown"
            service_counts[service] += 1
        
        return [
            {"service": service, "action_count": count}
            for service, count in sorted(service_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
    
    def _get_trend(self, actions: List[Dict], days: int) -> Dict:
        """Calculate trend compared to previous period"""
        if days <= 0:
            return {"direction": "stable", "change_percent": 0}
        
        cutoff_current = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_previous = cutoff_current - timedelta(days=days)
        
        current_count = len([a for a in actions if self._is_in_period(a, cutoff_current, None)])
        previous_count = len([a for a in actions if self._is_in_period(a, cutoff_previous, cutoff_current)])
        
        if previous_count == 0:
            return {"direction": "new", "change_percent": 100}
        
        change = ((current_count - previous_count) / previous_count) * 100
        direction = "up" if change > 5 else "down" if change < -5 else "stable"
        
        return {
            "direction": direction,
            "change_percent": round(change, 1),
            "current_period": current_count,
            "previous_period": previous_count
        }
    
    def _is_in_period(self, action: Dict, start: datetime, end: datetime = None) -> bool:
        """Check if action is within time period"""
        try:
            timestamp = action.get("timestamp", "")
            action_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            if action_time < start:
                return False
            if end and action_time >= end:
                return False
            return True
        except (ValueError, TypeError):
            return False
