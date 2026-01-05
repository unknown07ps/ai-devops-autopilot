"""
Production Knowledge Model
===========================
Continuously updated model of real production dependencies and behavior.
Learns and maintains a living representation of production architecture.

This module provides:
- Service dependency graph
- Behavioral baselines per service
- Communication pattern learning
- Impact radius calculation
- Architecture drift detection
"""

import json
import asyncio
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict
import logging
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("production_model")


class ServiceType(Enum):
    """Types of services in production"""
    API_GATEWAY = "api_gateway"
    MICROSERVICE = "microservice"
    DATABASE = "database"
    CACHE = "cache"
    MESSAGE_QUEUE = "message_queue"
    STORAGE = "storage"
    EXTERNAL = "external"
    LOAD_BALANCER = "load_balancer"
    CDN = "cdn"


class DependencyType(Enum):
    """Types of dependencies between services"""
    SYNC_HTTP = "sync_http"
    ASYNC_HTTP = "async_http"
    GRPC = "grpc"
    MESSAGE_QUEUE = "message_queue"
    DATABASE = "database"
    CACHE = "cache"
    FILESYSTEM = "filesystem"


class HealthStatus(Enum):
    """Service health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceNode:
    """A service in the production graph"""
    service_id: str
    name: str
    service_type: str
    
    # Ownership
    team: str
    owner: str
    
    # Criticality (1-4, 1=most critical)
    criticality_tier: int
    
    # Current state
    health_status: str
    replica_count: int
    current_version: str
    
    # Behavioral baselines
    avg_latency_ms: float
    avg_error_rate: float
    avg_requests_per_second: float
    avg_cpu_usage: float
    avg_memory_usage: float
    
    # Dependencies
    depends_on: List[str] = field(default_factory=list)
    depended_by: List[str] = field(default_factory=list)
    
    # Metadata
    last_deployment: Optional[str] = None
    last_incident: Optional[str] = None
    last_updated: str = ""
    
    # Learning
    behavior_samples: int = 0
    incident_count_30d: int = 0


@dataclass
class DependencyEdge:
    """A dependency between two services"""
    edge_id: str
    source_service: str
    target_service: str
    dependency_type: str
    
    # Criticality
    is_critical: bool  # Service fails without this dependency
    is_async: bool
    has_fallback: bool
    
    # Behavioral metrics
    avg_latency_ms: float
    avg_calls_per_second: float
    error_rate: float
    
    # Traffic patterns
    peak_hours: List[int] = field(default_factory=list)
    low_traffic_hours: List[int] = field(default_factory=list)
    
    # Learning
    observed_count: int = 0
    last_observed: str = ""


@dataclass
class ProductionTopology:
    """Complete production topology snapshot"""
    topology_id: str
    generated_at: str
    
    # Graph
    services: Dict[str, Dict]
    dependencies: List[Dict]
    
    # Statistics
    total_services: int
    total_dependencies: int
    critical_paths: List[List[str]]
    
    # Health summary
    healthy_services: int
    degraded_services: int
    unhealthy_services: int


class ProductionKnowledgeModel:
    """
    Continuously learns and maintains a living model of production.
    
    Features:
    - Auto-discovers services and dependencies
    - Learns behavioral baselines
    - Tracks communication patterns
    - Calculates blast radius
    - Detects architecture drift
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
        
        # In-memory graph
        self.services: Dict[str, ServiceNode] = {}
        self.dependencies: Dict[str, DependencyEdge] = {}
        
        # Configuration
        self.baseline_window_hours = 168  # 7 days
        self.learning_rate = 0.1  # Exponential moving average
        self.stale_threshold_hours = 24
        
        # Load existing model
        self._load_model()
        
        logger.info(f"[MODEL] Loaded production model: {len(self.services)} services")
    
    def _load_model(self):
        """Load model from Redis"""
        
        try:
            # Load services
            service_keys = self.redis.smembers("production_model:services")
            for key in service_keys:
                key_str = key.decode() if isinstance(key, bytes) else key
                data = self.redis.get(f"production_model:service:{key_str}")
                if data:
                    service_dict = json.loads(data)
                    self.services[key_str] = ServiceNode(**service_dict)
            
            # Load dependencies
            dep_keys = self.redis.smembers("production_model:dependencies")
            for key in dep_keys:
                key_str = key.decode() if isinstance(key, bytes) else key
                data = self.redis.get(f"production_model:dependency:{key_str}")
                if data:
                    dep_dict = json.loads(data)
                    self.dependencies[key_str] = DependencyEdge(**dep_dict)
                    
        except Exception as e:
            logger.error(f"[MODEL] Error loading model: {e}")
    
    def register_service(
        self,
        service_id: str,
        name: str,
        service_type: str = ServiceType.MICROSERVICE.value,
        team: str = "unknown",
        owner: str = "unknown",
        criticality_tier: int = 2
    ) -> ServiceNode:
        """Register a new service in the model"""
        
        service = ServiceNode(
            service_id=service_id,
            name=name,
            service_type=service_type,
            team=team,
            owner=owner,
            criticality_tier=criticality_tier,
            health_status=HealthStatus.UNKNOWN.value,
            replica_count=1,
            current_version="unknown",
            avg_latency_ms=0,
            avg_error_rate=0,
            avg_requests_per_second=0,
            avg_cpu_usage=0,
            avg_memory_usage=0,
            last_updated=datetime.now(timezone.utc).isoformat()
        )
        
        self.services[service_id] = service
        self._save_service(service)
        
        logger.info(f"[MODEL] Registered service: {name}")
        return service
    
    def register_dependency(
        self,
        source: str,
        target: str,
        dependency_type: str = DependencyType.SYNC_HTTP.value,
        is_critical: bool = False,
        has_fallback: bool = False
    ) -> DependencyEdge:
        """Register a dependency between services"""
        
        edge_id = f"{source}->{target}"
        
        edge = DependencyEdge(
            edge_id=edge_id,
            source_service=source,
            target_service=target,
            dependency_type=dependency_type,
            is_critical=is_critical,
            is_async=dependency_type in [DependencyType.MESSAGE_QUEUE.value, DependencyType.ASYNC_HTTP.value],
            has_fallback=has_fallback,
            avg_latency_ms=0,
            avg_calls_per_second=0,
            error_rate=0,
            last_observed=datetime.now(timezone.utc).isoformat()
        )
        
        self.dependencies[edge_id] = edge
        self._save_dependency(edge)
        
        # Update service nodes
        if source in self.services:
            if target not in self.services[source].depends_on:
                self.services[source].depends_on.append(target)
                self._save_service(self.services[source])
        
        if target in self.services:
            if source not in self.services[target].depended_by:
                self.services[target].depended_by.append(source)
                self._save_service(self.services[target])
        
        logger.info(f"[MODEL] Registered dependency: {source} -> {target}")
        return edge
    
    def learn_from_metrics(
        self,
        service_id: str,
        metrics: Dict
    ):
        """Learn behavioral baseline from metrics"""
        
        if service_id not in self.services:
            # Auto-register service
            self.register_service(service_id, service_id)
        
        service = self.services[service_id]
        
        # Exponential moving average update
        alpha = self.learning_rate
        
        if metrics.get("latency_p99_ms") is not None:
            service.avg_latency_ms = (
                alpha * metrics["latency_p99_ms"] +
                (1 - alpha) * service.avg_latency_ms
            )
        
        if metrics.get("error_rate") is not None:
            service.avg_error_rate = (
                alpha * metrics["error_rate"] +
                (1 - alpha) * service.avg_error_rate
            )
        
        if metrics.get("requests_per_second") is not None:
            service.avg_requests_per_second = (
                alpha * metrics["requests_per_second"] +
                (1 - alpha) * service.avg_requests_per_second
            )
        
        if metrics.get("cpu_usage") is not None:
            service.avg_cpu_usage = (
                alpha * metrics["cpu_usage"] +
                (1 - alpha) * service.avg_cpu_usage
            )
        
        if metrics.get("memory_usage") is not None:
            service.avg_memory_usage = (
                alpha * metrics["memory_usage"] +
                (1 - alpha) * service.avg_memory_usage
            )
        
        service.behavior_samples += 1
        service.last_updated = datetime.now(timezone.utc).isoformat()
        
        self._save_service(service)
    
    def learn_from_traffic(
        self,
        source: str,
        target: str,
        latency_ms: float,
        success: bool
    ):
        """Learn from observed traffic between services"""
        
        edge_id = f"{source}->{target}"
        
        if edge_id not in self.dependencies:
            # Auto-discover dependency
            self.register_dependency(source, target)
        
        edge = self.dependencies[edge_id]
        alpha = self.learning_rate
        
        # Update latency
        edge.avg_latency_ms = alpha * latency_ms + (1 - alpha) * edge.avg_latency_ms
        
        # Update error rate
        current_error = 0 if success else 1
        edge.error_rate = alpha * current_error + (1 - alpha) * edge.error_rate
        
        edge.observed_count += 1
        edge.last_observed = datetime.now(timezone.utc).isoformat()
        
        # Track peak hours
        current_hour = datetime.now(timezone.utc).hour
        if current_hour not in edge.peak_hours and len(edge.peak_hours) < 6:
            edge.peak_hours.append(current_hour)
        
        self._save_dependency(edge)
    
    def update_service_health(
        self,
        service_id: str,
        health: str,
        replica_count: int = None,
        version: str = None
    ):
        """Update service health status"""
        
        if service_id not in self.services:
            return
        
        service = self.services[service_id]
        service.health_status = health
        
        if replica_count is not None:
            service.replica_count = replica_count
        
        if version is not None:
            service.current_version = version
        
        service.last_updated = datetime.now(timezone.utc).isoformat()
        self._save_service(service)
    
    def record_deployment(self, service_id: str, version: str):
        """Record a deployment event"""
        
        if service_id not in self.services:
            self.register_service(service_id, service_id)
        
        service = self.services[service_id]
        service.current_version = version
        service.last_deployment = datetime.now(timezone.utc).isoformat()
        service.last_updated = datetime.now(timezone.utc).isoformat()
        
        self._save_service(service)
    
    def record_incident(self, service_id: str, incident_id: str):
        """Record an incident for a service"""
        
        if service_id not in self.services:
            return
        
        service = self.services[service_id]
        service.last_incident = datetime.now(timezone.utc).isoformat()
        service.incident_count_30d += 1
        
        self._save_service(service)
    
    def get_service(self, service_id: str) -> Optional[ServiceNode]:
        """Get a service by ID"""
        return self.services.get(service_id)
    
    def get_dependencies(self, service_id: str) -> List[DependencyEdge]:
        """Get all dependencies for a service"""
        return [
            edge for edge in self.dependencies.values()
            if edge.source_service == service_id
        ]
    
    def get_dependents(self, service_id: str) -> List[DependencyEdge]:
        """Get all services that depend on this service"""
        return [
            edge for edge in self.dependencies.values()
            if edge.target_service == service_id
        ]
    
    def calculate_blast_radius(self, service_id: str) -> Dict:
        """
        Calculate the blast radius if a service goes down.
        Returns all affected services and impact score.
        """
        
        if service_id not in self.services:
            return {"affected": [], "impact_score": 0}
        
        affected = set()
        visited = set()
        
        def dfs(current_id: str, depth: int):
            if current_id in visited or depth > 10:
                return
            visited.add(current_id)
            
            # Get services that depend on current
            for edge in self.get_dependents(current_id):
                if edge.is_critical and not edge.has_fallback:
                    affected.add(edge.source_service)
                    dfs(edge.source_service, depth + 1)
        
        dfs(service_id, 0)
        
        # Calculate impact score
        impact_score = 0
        for affected_id in affected:
            if affected_id in self.services:
                # Higher tier = lower score, so invert
                tier = self.services[affected_id].criticality_tier
                impact_score += (5 - tier) * 20
        
        # Add direct impact
        if service_id in self.services:
            tier = self.services[service_id].criticality_tier
            impact_score += (5 - tier) * 30
        
        return {
            "source_service": service_id,
            "affected_services": list(affected),
            "affected_count": len(affected),
            "impact_score": min(100, impact_score),
            "critical_path": service_id in self._get_critical_path_services()
        }
    
    def _get_critical_path_services(self) -> Set[str]:
        """Get services on critical path"""
        critical = set()
        
        for service in self.services.values():
            if service.criticality_tier == 1:
                critical.add(service.service_id)
                # Add all dependencies of tier-1 services
                for dep in service.depends_on:
                    critical.add(dep)
        
        return critical
    
    def detect_architecture_drift(self) -> List[Dict]:
        """Detect changes in architecture from baseline"""
        
        drifts = []
        now = datetime.now(timezone.utc)
        
        for service in self.services.values():
            # Check for stale services
            try:
                last_update = datetime.fromisoformat(service.last_updated.replace("Z", "+00:00"))
                hours_since_update = (now - last_update).total_seconds() / 3600
                
                if hours_since_update > self.stale_threshold_hours:
                    drifts.append({
                        "type": "stale_service",
                        "service": service.service_id,
                        "message": f"Service not updated in {hours_since_update:.0f} hours",
                        "severity": "warning"
                    })
            except:
                pass
            
            # Check for high error rate drift
            if service.avg_error_rate > 5 and service.behavior_samples > 100:
                drifts.append({
                    "type": "high_error_rate",
                    "service": service.service_id,
                    "message": f"Average error rate is {service.avg_error_rate:.1f}%",
                    "severity": "high"
                })
            
            # Check for missing tier-1 dependencies
            if service.criticality_tier == 1:
                if not service.depends_on:
                    drifts.append({
                        "type": "orphan_critical",
                        "service": service.service_id,
                        "message": "Tier-1 service has no registered dependencies",
                        "severity": "info"
                    })
        
        return drifts
    
    def get_topology(self) -> ProductionTopology:
        """Get complete production topology"""
        
        services_dict = {sid: asdict(s) for sid, s in self.services.items()}
        dependencies_list = [asdict(d) for d in self.dependencies.values()]
        
        # Calculate health summary
        healthy = sum(1 for s in self.services.values() if s.health_status == HealthStatus.HEALTHY.value)
        degraded = sum(1 for s in self.services.values() if s.health_status == HealthStatus.DEGRADED.value)
        unhealthy = sum(1 for s in self.services.values() if s.health_status == HealthStatus.UNHEALTHY.value)
        
        # Find critical paths (simplified - tier 1 services and their deps)
        critical_paths = []
        for service in self.services.values():
            if service.criticality_tier == 1:
                path = [service.service_id] + service.depends_on[:3]
                critical_paths.append(path)
        
        return ProductionTopology(
            topology_id=f"topo_{int(datetime.now(timezone.utc).timestamp())}",
            generated_at=datetime.now(timezone.utc).isoformat(),
            services=services_dict,
            dependencies=dependencies_list,
            total_services=len(self.services),
            total_dependencies=len(self.dependencies),
            critical_paths=critical_paths,
            healthy_services=healthy,
            degraded_services=degraded,
            unhealthy_services=unhealthy
        )
    
    def get_service_context(self, service_id: str) -> Dict:
        """Get full context for a service including dependencies and behavior"""
        
        if service_id not in self.services:
            return {"error": "Service not found"}
        
        service = self.services[service_id]
        dependencies = self.get_dependencies(service_id)
        dependents = self.get_dependents(service_id)
        blast_radius = self.calculate_blast_radius(service_id)
        
        return {
            "service": asdict(service),
            "dependencies": [asdict(d) for d in dependencies],
            "dependents": [asdict(d) for d in dependents],
            "dependency_count": len(dependencies),
            "dependent_count": len(dependents),
            "blast_radius": blast_radius,
            "behavioral_baseline": {
                "avg_latency_ms": service.avg_latency_ms,
                "avg_error_rate": service.avg_error_rate,
                "avg_rps": service.avg_requests_per_second,
                "avg_cpu": service.avg_cpu_usage,
                "avg_memory": service.avg_memory_usage,
                "samples": service.behavior_samples
            },
            "risk_factors": {
                "criticality_tier": service.criticality_tier,
                "incident_count_30d": service.incident_count_30d,
                "has_recent_incident": service.last_incident is not None
            }
        }
    
    def _save_service(self, service: ServiceNode):
        """Save service to Redis"""
        try:
            self.redis.set(
                f"production_model:service:{service.service_id}",
                json.dumps(asdict(service))
            )
            self.redis.sadd("production_model:services", service.service_id)
        except Exception as e:
            logger.error(f"[MODEL] Error saving service: {e}")
    
    def _save_dependency(self, edge: DependencyEdge):
        """Save dependency to Redis"""
        try:
            self.redis.set(
                f"production_model:dependency:{edge.edge_id}",
                json.dumps(asdict(edge))
            )
            self.redis.sadd("production_model:dependencies", edge.edge_id)
        except Exception as e:
            logger.error(f"[MODEL] Error saving dependency: {e}")
    
    def get_model_stats(self) -> Dict:
        """Get statistics about the production model"""
        
        topology = self.get_topology()
        drifts = self.detect_architecture_drift()
        
        # Calculate dependency density
        density = (
            len(self.dependencies) / (len(self.services) ** 2)
            if len(self.services) > 1 else 0
        )
        
        return {
            "total_services": len(self.services),
            "total_dependencies": len(self.dependencies),
            "healthy_services": topology.healthy_services,
            "degraded_services": topology.degraded_services,
            "unhealthy_services": topology.unhealthy_services,
            "tier_1_services": sum(1 for s in self.services.values() if s.criticality_tier == 1),
            "dependency_density": round(density, 3),
            "critical_paths": len(topology.critical_paths),
            "architecture_drifts": len(drifts),
            "drift_details": drifts[:5]
        }


# Convenience function
def get_production_model(redis_client) -> ProductionKnowledgeModel:
    """Get production knowledge model instance"""
    return ProductionKnowledgeModel(redis_client)
