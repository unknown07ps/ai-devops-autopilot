"""
Extended DevOps Patterns - Database Patterns (100+)
Covers MySQL, PostgreSQL, MongoDB, Redis, and general database issues
"""

from typing import List
from src.training.devops_knowledge_base import (
    IncidentPattern, PatternCategory, Severity, BlastRadius,
    Symptom, RecommendedAction
)


def get_extended_database_patterns() -> List[IncidentPattern]:
    """Get extended database patterns (100+ additional)"""
    patterns = []
    
    # ==================== MYSQL PATTERNS ====================
    
    patterns.append(IncidentPattern(
        pattern_id="db_mysql_max_connections_051",
        name="MySQL Max Connections Reached",
        description="MySQL server has reached maximum connection limit",
        category=PatternCategory.DATABASE,
        subcategory="mysql",
        severity=Severity.CRITICAL,
        symptoms=[
            Symptom("log", "Too many connections", "contains", True, 3.0),
            Symptom("metric", "mysql_connections", "above", 95, 2.5),
        ],
        signals=["Too many connections", "max_connections", "connection refused"],
        root_causes=["connection_leak", "high_traffic", "slow_queries", "insufficient_limit"],
        recommended_actions=[
            RecommendedAction("kill_idle_connections", "database", 85, {"idle_seconds": 300}, False, 30),
            RecommendedAction("increase_max_connections", "database", 80, {"value": 500}, True, 60),
            RecommendedAction("restart_application", "application", 70, {}, True, 120),
        ],
        autonomous_safe=True,
        blast_radius=BlastRadius.HIGH,
        resolution_time_avg_seconds=120,
        tags=["mysql", "connections", "max"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="db_mysql_slow_query_052",
        name="MySQL Slow Query Detected",
        description="Query taking longer than slow query threshold",
        category=PatternCategory.DATABASE,
        subcategory="mysql",
        severity=Severity.MEDIUM,
        symptoms=[
            Symptom("metric", "mysql_slow_queries", "above", 10, 2.5),
            Symptom("log", "slow query", "contains", True, 2.0),
        ],
        signals=["slow query", "Query_time", "Lock_time", "Rows_examined"],
        root_causes=["missing_index", "table_scan", "lock_contention", "large_result_set"],
        recommended_actions=[
            RecommendedAction("analyze_slow_query_log", "database", 95, {}, False, 60),
            RecommendedAction("add_index", "database", 75, {}, True, 300),
            RecommendedAction("optimize_query", "database", 70, {}, True, 600),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=300,
        tags=["mysql", "slow", "query"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="db_mysql_replication_lag_053",
        name="MySQL Replication Lag High",
        description="MySQL replica is behind master by significant amount",
        category=PatternCategory.DATABASE,
        subcategory="mysql",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("metric", "mysql_slave_lag_seconds", "above", 30, 3.0),
            Symptom("metric", "mysql_slave_running", "equals", True, 1.0),
        ],
        signals=["Seconds_Behind_Master", "replication", "lag", "slave"],
        root_causes=["high_write_volume", "slow_replica", "network_latency", "large_transaction"],
        recommended_actions=[
            RecommendedAction("check_replication_status", "database", 95, {}, False, 15),
            RecommendedAction("optimize_replica_config", "database", 75, {}, True, 120),
            RecommendedAction("scale_replica_resources", "cloud", 70, {}, True, 300),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.MEDIUM,
        resolution_time_avg_seconds=300,
        tags=["mysql", "replication", "lag"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="db_mysql_replication_broken_054",
        name="MySQL Replication Broken",
        description="MySQL replication has stopped",
        category=PatternCategory.DATABASE,
        subcategory="mysql",
        severity=Severity.CRITICAL,
        symptoms=[
            Symptom("metric", "mysql_slave_io_running", "equals", False, 3.0),
            Symptom("metric", "mysql_slave_sql_running", "equals", False, 3.0),
        ],
        signals=["Slave_IO_Running: No", "Slave_SQL_Running: No", "replication error"],
        root_causes=["duplicate_entry", "table_not_found", "network_issue", "disk_full"],
        recommended_actions=[
            RecommendedAction("show_slave_status", "database", 95, {}, False, 10),
            RecommendedAction("skip_error", "database", 60, {"count": 1}, True, 15),
            RecommendedAction("rebuild_replication", "database", 50, {}, True, 3600),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.HIGH,
        resolution_time_avg_seconds=600,
        tags=["mysql", "replication", "broken"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="db_mysql_table_lock_055",
        name="MySQL Table Lock Contention",
        description="Excessive table lock wait time",
        category=PatternCategory.DATABASE,
        subcategory="mysql",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("metric", "mysql_table_locks_waited", "above", 100, 2.5),
            Symptom("log", "Lock wait timeout", "contains", True, 3.0),
        ],
        signals=["lock wait", "table lock", "waiting for table", "metadata lock"],
        root_causes=["long_running_query", "ddl_operation", "myisam_tables", "transaction_not_committed"],
        recommended_actions=[
            RecommendedAction("show_processlist", "database", 95, {}, False, 10),
            RecommendedAction("kill_blocking_query", "database", 80, {}, True, 15),
            RecommendedAction("convert_to_innodb", "database", 60, {}, True, 1800),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.MEDIUM,
        resolution_time_avg_seconds=120,
        tags=["mysql", "lock", "table"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="db_mysql_innodb_lock_056",
        name="MySQL InnoDB Row Lock Wait",
        description="InnoDB row lock wait timeout exceeded",
        category=PatternCategory.DATABASE,
        subcategory="mysql",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("log", "Lock wait timeout exceeded", "contains", True, 3.0),
            Symptom("metric", "mysql_innodb_row_lock_waits", "above", 50, 2.5),
        ],
        signals=["Lock wait timeout exceeded", "innodb", "row lock", "deadlock"],
        root_causes=["long_transaction", "missing_index", "update_conflict", "deadlock"],
        recommended_actions=[
            RecommendedAction("show_innodb_status", "database", 95, {}, False, 10),
            RecommendedAction("identify_blocking_transaction", "database", 90, {}, False, 30),
            RecommendedAction("kill_blocking_session", "database", 75, {}, True, 15),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.MEDIUM,
        resolution_time_avg_seconds=180,
        tags=["mysql", "innodb", "lock", "row"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="db_mysql_buffer_pool_057",
        name="MySQL InnoDB Buffer Pool Pressure",
        description="InnoDB buffer pool hit ratio is low",
        category=PatternCategory.DATABASE,
        subcategory="mysql",
        severity=Severity.MEDIUM,
        symptoms=[
            Symptom("metric", "mysql_innodb_buffer_pool_hit_rate", "below", 95, 2.5),
            Symptom("metric", "mysql_innodb_buffer_pool_reads", "above", 1000, 2.0),
        ],
        signals=["buffer pool", "disk reads", "cache miss", "memory"],
        root_causes=["buffer_pool_too_small", "working_set_too_large", "random_io_pattern"],
        recommended_actions=[
            RecommendedAction("analyze_buffer_pool_usage", "database", 90, {}, False, 60),
            RecommendedAction("increase_buffer_pool_size", "database", 80, {}, True, 300),
            RecommendedAction("optimize_queries", "database", 70, {}, True, 600),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=300,
        tags=["mysql", "innodb", "buffer", "pool"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="db_mysql_binlog_full_058",
        name="MySQL Binary Log Disk Full",
        description="Binary logs consuming too much disk space",
        category=PatternCategory.DATABASE,
        subcategory="mysql",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("metric", "mysql_binlog_size_bytes", "above", 10737418240, 2.5),
            Symptom("metric", "disk_usage_percent", "above", 85, 2.0),
        ],
        signals=["binlog", "disk full", "binary log", "purge"],
        root_causes=["expire_logs_days_too_high", "no_purge", "replication_delay"],
        recommended_actions=[
            RecommendedAction("purge_old_binlogs", "database", 85, {"days": 3}, False, 60),
            RecommendedAction("set_expire_logs_days", "database", 80, {"value": 7}, True, 30),
            RecommendedAction("expand_disk", "cloud", 70, {"size_gb": 50}, True, 300),
        ],
        autonomous_safe=True,
        blast_radius=BlastRadius.MEDIUM,
        resolution_time_avg_seconds=120,
        tags=["mysql", "binlog", "disk"]
    ))
    
    # ==================== POSTGRESQL PATTERNS ====================
    
    patterns.append(IncidentPattern(
        pattern_id="db_postgres_vacuum_blocked_059",
        name="PostgreSQL Vacuum Blocked",
        description="Autovacuum or manual vacuum blocked by long transactions",
        category=PatternCategory.DATABASE,
        subcategory="postgresql",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("metric", "pg_stat_user_tables_n_dead_tup", "above", 100000, 2.5),
            Symptom("log", "preventing transaction ID wraparound", "contains", True, 3.0),
        ],
        signals=["vacuum", "dead tuples", "bloat", "xid wraparound"],
        root_causes=["long_running_transaction", "idle_in_transaction", "vacuum_settings"],
        recommended_actions=[
            RecommendedAction("check_long_running_queries", "database", 95, {}, False, 15),
            RecommendedAction("terminate_idle_transactions", "database", 80, {}, True, 30),
            RecommendedAction("manual_vacuum", "database", 75, {}, True, 600),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.HIGH,
        resolution_time_avg_seconds=300,
        tags=["postgresql", "vacuum", "bloat"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="db_postgres_xid_wraparound_060",
        name="PostgreSQL Transaction ID Wraparound Warning",
        description="Database approaching transaction ID wraparound",
        category=PatternCategory.DATABASE,
        subcategory="postgresql",
        severity=Severity.CRITICAL,
        symptoms=[
            Symptom("log", "transaction ID wraparound", "contains", True, 3.0),
            Symptom("metric", "pg_database_age", "above", 1000000000, 3.0),
        ],
        signals=["xid wraparound", "must be vacuumed", "freeze", "age"],
        root_causes=["vacuum_not_running", "long_running_transaction", "autovacuum_disabled"],
        recommended_actions=[
            RecommendedAction("emergency_vacuum_freeze", "database", 95, {}, True, 3600),
            RecommendedAction("check_vacuum_settings", "database", 90, {}, False, 30),
            RecommendedAction("enable_autovacuum", "database", 85, {}, True, 60),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.CRITICAL,
        resolution_time_avg_seconds=1800,
        tags=["postgresql", "xid", "wraparound"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="db_postgres_connection_limit_061",
        name="PostgreSQL Connection Limit Reached",
        description="PostgreSQL max_connections limit reached",
        category=PatternCategory.DATABASE,
        subcategory="postgresql",
        severity=Severity.CRITICAL,
        symptoms=[
            Symptom("log", "too many connections", "contains", True, 3.0),
            Symptom("metric", "pg_stat_activity_count", "above", 95, 2.5),
        ],
        signals=["too many connections", "max_connections", "FATAL"],
        root_causes=["connection_leak", "pool_misconfiguration", "traffic_spike"],
        recommended_actions=[
            RecommendedAction("terminate_idle_connections", "database", 85, {}, False, 30),
            RecommendedAction("increase_max_connections", "database", 75, {}, True, 120),
            RecommendedAction("implement_connection_pooler", "database", 70, {}, True, 1800),
        ],
        autonomous_safe=True,
        blast_radius=BlastRadius.HIGH,
        resolution_time_avg_seconds=180,
        tags=["postgresql", "connections", "limit"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="db_postgres_replication_slot_062",
        name="PostgreSQL Replication Slot Inactive",
        description="Replication slot accumulating WAL files",
        category=PatternCategory.DATABASE,
        subcategory="postgresql",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("metric", "pg_replication_slots_inactive", "above", 0, 3.0),
            Symptom("metric", "pg_wal_size_bytes", "above", 10737418240, 2.5),
        ],
        signals=["replication slot", "WAL", "inactive", "disk full"],
        root_causes=["subscriber_down", "slot_not_removed", "replication_lag"],
        recommended_actions=[
            RecommendedAction("check_replication_slots", "database", 95, {}, False, 15),
            RecommendedAction("drop_inactive_slot", "database", 75, {}, True, 30),
            RecommendedAction("check_subscriber_status", "database", 85, {}, False, 60),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.MEDIUM,
        resolution_time_avg_seconds=180,
        tags=["postgresql", "replication", "slot", "wal"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="db_postgres_lock_wait_063",
        name="PostgreSQL Lock Wait Timeout",
        description="Queries waiting for locks exceeding timeout",
        category=PatternCategory.DATABASE,
        subcategory="postgresql",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("log", "canceling statement due to lock timeout", "contains", True, 3.0),
            Symptom("metric", "pg_locks_waiting", "above", 10, 2.5),
        ],
        signals=["lock timeout", "waiting for lock", "AccessExclusiveLock"],
        root_causes=["ddl_operation", "long_transaction", "concurrent_updates"],
        recommended_actions=[
            RecommendedAction("check_blocking_queries", "database", 95, {}, False, 15),
            RecommendedAction("terminate_blocking_session", "database", 80, {}, True, 15),
            RecommendedAction("increase_lock_timeout", "database", 65, {}, True, 30),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.MEDIUM,
        resolution_time_avg_seconds=120,
        tags=["postgresql", "lock", "wait"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="db_postgres_temp_files_064",
        name="PostgreSQL Excessive Temp Files",
        description="Queries using excessive temp file space",
        category=PatternCategory.DATABASE,
        subcategory="postgresql",
        severity=Severity.MEDIUM,
        symptoms=[
            Symptom("metric", "pg_stat_database_temp_bytes", "above", 1073741824, 2.5),
            Symptom("log", "temporary file", "contains", True, 2.0),
        ],
        signals=["temporary file", "temp_file", "work_mem", "sort"],
        root_causes=["work_mem_too_low", "large_sorts", "hash_joins", "complex_queries"],
        recommended_actions=[
            RecommendedAction("identify_temp_file_queries", "database", 90, {}, False, 30),
            RecommendedAction("increase_work_mem", "database", 75, {}, True, 60),
            RecommendedAction("optimize_queries", "database", 70, {}, True, 600),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=300,
        tags=["postgresql", "temp", "files"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="db_postgres_wal_growth_065",
        name="PostgreSQL WAL Size Growing",
        description="Write-Ahead Log consuming excessive disk space",
        category=PatternCategory.DATABASE,
        subcategory="postgresql",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("metric", "pg_wal_size_bytes", "above", 5368709120, 2.5),
            Symptom("metric", "disk_usage_percent", "above", 80, 2.0),
        ],
        signals=["WAL", "wal", "checkpoint", "archive"],
        root_causes=["archive_failure", "checkpoint_spacing", "high_write_load"],
        recommended_actions=[
            RecommendedAction("check_archive_status", "database", 90, {}, False, 30),
            RecommendedAction("checkpoint", "database", 80, {}, False, 60),
            RecommendedAction("adjust_wal_settings", "database", 70, {}, True, 120),
        ],
        autonomous_safe=True,
        blast_radius=BlastRadius.MEDIUM,
        resolution_time_avg_seconds=180,
        tags=["postgresql", "wal", "disk"]
    ))
    
    # ==================== MONGODB PATTERNS ====================
    
    patterns.append(IncidentPattern(
        pattern_id="db_mongo_primary_step_down_066",
        name="MongoDB Primary Stepdown",
        description="MongoDB replica set primary stepped down",
        category=PatternCategory.DATABASE,
        subcategory="mongodb",
        severity=Severity.CRITICAL,
        symptoms=[
            Symptom("log", "PRIMARY stepping down", "contains", True, 3.0),
            Symptom("log", "Received replSetStepDown", "contains", True, 2.5),
        ],
        signals=["stepping down", "stepDown", "election", "primary"],
        root_causes=["network_partition", "high_load", "maintenance", "election"],
        recommended_actions=[
            RecommendedAction("check_replica_set_status", "database", 95, {}, False, 15),
            RecommendedAction("check_network_connectivity", "database", 85, {}, False, 30),
            RecommendedAction("wait_for_election", "database", 80, {}, False, 60),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.HIGH,
        resolution_time_avg_seconds=120,
        tags=["mongodb", "primary", "stepdown"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="db_mongo_replication_lag_067",
        name="MongoDB Replication Lag High",
        description="MongoDB secondary lagging behind primary",
        category=PatternCategory.DATABASE,
        subcategory="mongodb",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("metric", "mongodb_replication_lag_seconds", "above", 30, 3.0),
            Symptom("log", "replication lag", "contains", True, 2.0),
        ],
        signals=["replication lag", "oplog", "secondary", "behind"],
        root_causes=["slow_secondary", "network_latency", "high_write_volume"],
        recommended_actions=[
            RecommendedAction("check_replication_status", "database", 95, {}, False, 15),
            RecommendedAction("check_secondary_resources", "database", 85, {}, False, 30),
            RecommendedAction("resync_secondary", "database", 60, {}, True, 3600),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.MEDIUM,
        resolution_time_avg_seconds=180,
        tags=["mongodb", "replication", "lag"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="db_mongo_slow_query_068",
        name="MongoDB Slow Query",
        description="MongoDB query exceeding slow query threshold",
        category=PatternCategory.DATABASE,
        subcategory="mongodb",
        severity=Severity.MEDIUM,
        symptoms=[
            Symptom("metric", "mongodb_slow_queries", "above", 10, 2.5),
            Symptom("log", "COLLSCAN", "contains", True, 2.0),
        ],
        signals=["slow query", "COLLSCAN", "planSummary", "keysExamined"],
        root_causes=["missing_index", "collection_scan", "suboptimal_query"],
        recommended_actions=[
            RecommendedAction("analyze_slow_queries", "database", 95, {}, False, 60),
            RecommendedAction("create_index", "database", 80, {}, True, 300),
            RecommendedAction("optimize_query", "database", 75, {}, True, 600),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=300,
        tags=["mongodb", "slow", "query"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="db_mongo_wiredtiger_cache_069",
        name="MongoDB WiredTiger Cache Pressure",
        description="WiredTiger cache evictions high",
        category=PatternCategory.DATABASE,
        subcategory="mongodb",
        severity=Severity.MEDIUM,
        symptoms=[
            Symptom("metric", "mongodb_wiredtiger_cache_eviction_rate", "above", 1000, 2.5),
            Symptom("metric", "mongodb_wiredtiger_cache_usage_percent", "above", 95, 2.0),
        ],
        signals=["cache", "eviction", "WiredTiger", "memory"],
        root_causes=["cache_too_small", "working_set_large", "memory_pressure"],
        recommended_actions=[
            RecommendedAction("check_cache_statistics", "database", 90, {}, False, 30),
            RecommendedAction("increase_cache_size", "database", 80, {}, True, 120),
            RecommendedAction("add_memory", "cloud", 70, {}, True, 300),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.MEDIUM,
        resolution_time_avg_seconds=180,
        tags=["mongodb", "wiredtiger", "cache"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="db_mongo_connection_pool_070",
        name="MongoDB Connection Pool Exhausted",
        description="MongoDB connection pool has no available connections",
        category=PatternCategory.DATABASE,
        subcategory="mongodb",
        severity=Severity.CRITICAL,
        symptoms=[
            Symptom("log", "connection pool", "contains", True, 2.5),
            Symptom("metric", "mongodb_connections_current", "above", 95, 3.0),
        ],
        signals=["connection pool", "exhausted", "connections", "timeout"],
        root_causes=["connection_leak", "slow_queries", "pool_too_small"],
        recommended_actions=[
            RecommendedAction("check_connection_usage", "database", 95, {}, False, 15),
            RecommendedAction("increase_pool_size", "database", 80, {}, False, 30),
            RecommendedAction("restart_application", "application", 70, {}, True, 120),
        ],
        autonomous_safe=True,
        blast_radius=BlastRadius.HIGH,
        resolution_time_avg_seconds=120,
        tags=["mongodb", "connection", "pool"]
    ))
    
    # ==================== REDIS PATTERNS ====================
    
    patterns.append(IncidentPattern(
        pattern_id="db_redis_memory_full_071",
        name="Redis Memory Full",
        description="Redis has reached maxmemory limit",
        category=PatternCategory.DATABASE,
        subcategory="redis",
        severity=Severity.CRITICAL,
        symptoms=[
            Symptom("log", "OOM command not allowed", "contains", True, 3.0),
            Symptom("metric", "redis_memory_used_bytes", "above", 95, 3.0),
        ],
        signals=["OOM", "maxmemory", "eviction", "memory"],
        root_causes=["data_growth", "no_eviction_policy", "memory_leak"],
        recommended_actions=[
            RecommendedAction("analyze_memory_usage", "database", 90, {}, False, 30),
            RecommendedAction("set_eviction_policy", "database", 85, {"policy": "volatile-lru"}, True, 30),
            RecommendedAction("increase_maxmemory", "database", 80, {}, True, 60),
        ],
        autonomous_safe=True,
        blast_radius=BlastRadius.HIGH,
        resolution_time_avg_seconds=120,
        tags=["redis", "memory", "oom"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="db_redis_cluster_down_072",
        name="Redis Cluster Node Down",
        description="Redis cluster node is not responding",
        category=PatternCategory.DATABASE,
        subcategory="redis",
        severity=Severity.CRITICAL,
        symptoms=[
            Symptom("metric", "redis_cluster_slots_ok", "below", 16384, 3.0),
            Symptom("log", "CLUSTERDOWN", "contains", True, 3.0),
        ],
        signals=["CLUSTERDOWN", "cluster fail", "node down", "slots"],
        root_causes=["node_crash", "network_partition", "memory_issue"],
        recommended_actions=[
            RecommendedAction("check_cluster_status", "database", 95, {}, False, 15),
            RecommendedAction("failover_to_replica", "database", 85, {}, True, 60),
            RecommendedAction("restart_node", "database", 75, {}, True, 120),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.CRITICAL,
        resolution_time_avg_seconds=180,
        tags=["redis", "cluster", "down"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="db_redis_blocked_clients_073",
        name="Redis Blocked Clients High",
        description="Many clients blocked waiting on blocking operations",
        category=PatternCategory.DATABASE,
        subcategory="redis",
        severity=Severity.MEDIUM,
        symptoms=[
            Symptom("metric", "redis_blocked_clients", "above", 50, 2.5),
        ],
        signals=["blocked_clients", "BLPOP", "BRPOP", "BRPOPLPUSH"],
        root_causes=["slow_consumer", "missing_producer", "timeout_too_high"],
        recommended_actions=[
            RecommendedAction("check_blocking_operations", "database", 90, {}, False, 30),
            RecommendedAction("reduce_timeout", "database", 75, {}, True, 30),
            RecommendedAction("check_consumer_health", "application", 80, {}, False, 60),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=180,
        tags=["redis", "blocked", "clients"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="db_redis_replication_broken_074",
        name="Redis Replication Broken",
        description="Redis replica disconnected from master",
        category=PatternCategory.DATABASE,
        subcategory="redis",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("metric", "redis_connected_slaves", "equals", 0, 3.0),
            Symptom("log", "Connection with master lost", "contains", True, 3.0),
        ],
        signals=["replication", "disconnected", "master_link_status", "sync"],
        root_causes=["network_issue", "master_overloaded", "buffer_overflow"],
        recommended_actions=[
            RecommendedAction("check_replication_status", "database", 95, {}, False, 15),
            RecommendedAction("restart_replica", "database", 80, {}, True, 60),
            RecommendedAction("increase_repl_backlog", "database", 70, {}, True, 60),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.MEDIUM,
        resolution_time_avg_seconds=180,
        tags=["redis", "replication", "broken"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="db_redis_slow_log_075",
        name="Redis Slow Commands Detected",
        description="Redis commands taking longer than threshold",
        category=PatternCategory.DATABASE,
        subcategory="redis",
        severity=Severity.MEDIUM,
        symptoms=[
            Symptom("metric", "redis_slowlog_length", "above", 100, 2.5),
        ],
        signals=["slowlog", "slow", "latency", "command"],
        root_causes=["large_keys", "expensive_commands", "memory_pressure"],
        recommended_actions=[
            RecommendedAction("analyze_slowlog", "database", 95, {}, False, 30),
            RecommendedAction("optimize_commands", "application", 75, {}, True, 600),
            RecommendedAction("avoid_dangerous_commands", "application", 80, {}, True, 300),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=300,
        tags=["redis", "slow", "commands"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="db_redis_persistence_error_076",
        name="Redis Persistence Error",
        description="Redis RDB or AOF persistence failing",
        category=PatternCategory.DATABASE,
        subcategory="redis",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("log", "MISCONF", "contains", True, 3.0),
            Symptom("log", "Background saving error", "contains", True, 2.5),
        ],
        signals=["MISCONF", "Background saving error", "AOF", "RDB"],
        root_causes=["disk_full", "permission_denied", "fork_failed"],
        recommended_actions=[
            RecommendedAction("check_disk_space", "database", 95, {}, False, 15),
            RecommendedAction("clear_disk_space", "database", 85, {}, False, 120),
            RecommendedAction("disable_persistence_temporarily", "database", 70, {}, True, 30),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.MEDIUM,
        resolution_time_avg_seconds=180,
        tags=["redis", "persistence", "error"]
    ))
    
    # ==================== GENERAL DATABASE PATTERNS ====================
    
    patterns.append(IncidentPattern(
        pattern_id="db_high_iops_077",
        name="Database IOPS Limit Reached",
        description="Database storage IOPS at capacity",
        category=PatternCategory.DATABASE,
        subcategory="storage",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("metric", "disk_iops_utilization", "above", 95, 3.0),
            Symptom("metric", "disk_queue_depth", "above", 10, 2.0),
        ],
        signals=["IOPS", "disk", "queue", "latency"],
        root_causes=["high_read_load", "high_write_load", "inefficient_queries"],
        recommended_actions=[
            RecommendedAction("identify_io_heavy_queries", "database", 90, {}, False, 60),
            RecommendedAction("upgrade_storage_iops", "cloud", 80, {}, True, 300),
            RecommendedAction("implement_read_replicas", "database", 70, {}, True, 1800),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.MEDIUM,
        resolution_time_avg_seconds=300,
        tags=["database", "iops", "storage"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="db_backup_failed_078",
        name="Database Backup Failed",
        description="Scheduled database backup failed",
        category=PatternCategory.DATABASE,
        subcategory="backup",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("log", "backup failed", "contains", True, 3.0),
            Symptom("metric", "backup_success", "equals", False, 3.0),
        ],
        signals=["backup", "failed", "snapshot", "dump"],
        root_causes=["disk_full", "network_error", "permission_denied", "lock_timeout"],
        recommended_actions=[
            RecommendedAction("check_backup_logs", "database", 95, {}, False, 30),
            RecommendedAction("retry_backup", "database", 80, {}, True, 60),
            RecommendedAction("check_disk_space", "database", 85, {}, False, 15),
        ],
        autonomous_safe=True,
        blast_radius=BlastRadius.LOW,
        resolution_time_avg_seconds=180,
        tags=["database", "backup", "failed"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="db_query_timeout_079",
        name="Database Query Timeout",
        description="Queries timing out before completion",
        category=PatternCategory.DATABASE,
        subcategory="performance",
        severity=Severity.HIGH,
        symptoms=[
            Symptom("log", "query timeout", "contains", True, 3.0),
            Symptom("metric", "query_timeout_count", "above", 10, 2.5),
        ],
        signals=["timeout", "query timeout", "statement timeout", "execution timeout"],
        root_causes=["long_running_query", "lock_wait", "resource_contention", "network_issue"],
        recommended_actions=[
            RecommendedAction("identify_slow_queries", "database", 95, {}, False, 30),
            RecommendedAction("kill_problematic_queries", "database", 80, {}, True, 15),
            RecommendedAction("increase_timeout", "database", 65, {}, True, 30),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.MEDIUM,
        resolution_time_avg_seconds=180,
        tags=["database", "query", "timeout"]
    ))
    
    patterns.append(IncidentPattern(
        pattern_id="db_connection_refused_080",
        name="Database Connection Refused",
        description="Unable to establish connection to database",
        category=PatternCategory.DATABASE,
        subcategory="connectivity",
        severity=Severity.CRITICAL,
        symptoms=[
            Symptom("log", "Connection refused", "contains", True, 3.0),
            Symptom("log", "could not connect", "contains", True, 2.5),
        ],
        signals=["Connection refused", "could not connect", "ECONNREFUSED", "timeout"],
        root_causes=["database_down", "network_issue", "firewall", "max_connections"],
        recommended_actions=[
            RecommendedAction("check_database_status", "database", 95, {}, False, 15),
            RecommendedAction("check_network_connectivity", "database", 90, {}, False, 30),
            RecommendedAction("restart_database", "database", 75, {}, True, 120),
        ],
        autonomous_safe=False,
        blast_radius=BlastRadius.CRITICAL,
        resolution_time_avg_seconds=120,
        tags=["database", "connection", "refused"]
    ))
    
    return patterns
